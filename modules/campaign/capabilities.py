from __future__ import annotations

import inspect
from collections.abc import Callable, Generator, Mapping
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from modules.missions.database import MissionStep
from modules.modes import get_bot_mode_by_name
from modules.modes._interface import BotModeError


_ALLOWED_MODULES = ("modules.campaign", "modules.clock", "modules.modes")
_LOCAL_NAMESPACE = "campaign"


def campaign_capability(function: Callable) -> Callable:
    """Mark a Campaign method as callable from the trusted mission catalogue."""
    setattr(function, "__campaign_capability__", True)
    return function


@dataclass(frozen=True)
class ResolvedCapability:
    reference: str
    callable: Callable[..., object]
    arguments: dict[str, object]
    delegate: object | None = None

    def run(self) -> Generator:
        result = self.callable(**self.arguments)
        if not isinstance(result, Generator):
            raise BotModeError(
                f"Campaign capability did not return a generator: {self.reference}"
            )
        yield from result


class CampaignCapabilityResolver:
    """Resolve trusted catalogue references without evaluating arbitrary text."""

    def __init__(
        self,
        bindings: Mapping[str, object],
        *,
        campaign: object | None = None,
    ):
        self._bindings = dict(bindings)
        self._campaign = campaign

    def resolve(
        self,
        reference: str,
        parameters: Mapping[str, object],
        step: MissionStep,
        rules: Mapping[str, object] | None = None,
    ) -> ResolvedCapability:
        if not isinstance(reference, str) or not reference:
            raise BotModeError("Campaign capability reference must be a non-empty string.")
        if not isinstance(parameters, Mapping):
            raise BotModeError(f"Campaign parameters must be an object: {reference}")

        kind, separator, target = reference.partition(":")
        if not separator or kind not in {"function", "controller", "mode"}:
            raise BotModeError(f"Unsupported Campaign capability reference: {reference}")

        resolved = self._resolve_value(dict(parameters), step, rules or {})
        if not isinstance(resolved, dict):
            raise BotModeError(f"Campaign parameters must resolve to an object: {reference}")

        if kind == "function":
            return self._resolve_function(reference, target, resolved)
        if kind == "mode":
            return self._resolve_mode(reference, target, resolved)
        return self._resolve_controller(reference, target, resolved)

    def _resolve_function(
        self,
        reference: str,
        target: str,
        arguments: dict[str, object],
    ) -> ResolvedCapability:
        namespace, separator, symbol = target.rpartition(":")
        if not separator or not namespace or not symbol:
            raise BotModeError(f"Invalid Campaign function reference: {reference}")

        if namespace == _LOCAL_NAMESPACE:
            if self._campaign is None:
                raise BotModeError(f"Campaign namespace is unavailable: {reference}")
            function = getattr(self._campaign, symbol, None)
            unbound_function = getattr(function, "__func__", function)
            if function is None or not getattr(
                unbound_function, "__campaign_capability__", False
            ):
                raise BotModeError(f"Campaign function is not allowed: {reference}")
        else:
            module = self._internal_module(namespace, reference)
            if symbol.startswith("_"):
                raise BotModeError(f"Private Campaign function is not allowed: {reference}")
            function = getattr(module, symbol, None)
            if function is None or not inspect.isfunction(function):
                raise BotModeError(f"Campaign function does not exist: {reference}")

        self._validate_arguments(function, arguments, reference)
        self._validate_generator(function, reference)
        return ResolvedCapability(reference, function, arguments)

    def _resolve_mode(
        self,
        reference: str,
        target: str,
        parameters: dict[str, object],
    ) -> ResolvedCapability:
        mode_name, separator, method_name = target.rpartition(":")
        if not separator or not mode_name or not method_name or method_name.startswith("_"):
            raise BotModeError(f"Invalid Campaign mode reference: {reference}")
        if mode_name == "Campaign":
            raise BotModeError("Campaign cannot delegate a step to itself.")

        mode_class = get_bot_mode_by_name(mode_name)
        if mode_class is None:
            raise BotModeError(f"Campaign mode is not registered: {mode_name}")
        constructor, arguments = self._split_object_parameters(parameters, reference)
        self._validate_arguments(mode_class, constructor, reference)
        mode = mode_class(**constructor)
        method = getattr(mode, method_name, None)
        if method is None or not callable(method):
            raise BotModeError(f"Campaign mode method does not exist: {reference}")
        self._validate_arguments(method, arguments, reference)
        self._validate_generator(method, reference)
        return ResolvedCapability(reference, method, arguments, mode)

    def _resolve_controller(
        self,
        reference: str,
        target: str,
        parameters: dict[str, object],
    ) -> ResolvedCapability:
        module_name, class_name, method_name = self._controller_target(target, reference)
        module = self._internal_module(module_name, reference)
        if not class_name.endswith("Controller") or class_name.startswith("_"):
            raise BotModeError(f"Campaign controller is not allowed: {reference}")
        controller_class = getattr(module, class_name, None)
        if controller_class is None or not inspect.isclass(controller_class):
            raise BotModeError(f"Campaign controller does not exist: {reference}")

        constructor, arguments = self._split_object_parameters(parameters, reference)
        self._validate_arguments(controller_class, constructor, reference)
        controller = controller_class(**constructor)
        method = getattr(controller, method_name, None)
        if method_name.startswith("_") or method is None or not callable(method):
            raise BotModeError(f"Campaign controller method does not exist: {reference}")
        self._validate_arguments(method, arguments, reference)
        self._validate_generator(method, reference)
        return ResolvedCapability(reference, method, arguments, controller)

    @staticmethod
    def _controller_target(target: str, reference: str) -> tuple[str, str, str]:
        module_and_class, separator, method_name = target.rpartition(":")
        module_name, dot, class_name = module_and_class.rpartition(".")
        if not separator or not dot or not module_name or not class_name or not method_name:
            raise BotModeError(f"Invalid Campaign controller reference: {reference}")
        return module_name, class_name, method_name

    @staticmethod
    def _split_object_parameters(
        parameters: dict[str, object], reference: str
    ) -> tuple[dict[str, object], dict[str, object]]:
        unexpected = set(parameters) - {"constructor", "arguments"}
        if unexpected:
            raise BotModeError(
                f"Unsupported Campaign parameters for {reference}: {sorted(unexpected)}"
            )
        constructor = parameters.get("constructor", {})
        arguments = parameters.get("arguments", {})
        if not isinstance(constructor, dict) or not isinstance(arguments, dict):
            raise BotModeError(
                f"Campaign constructor and arguments must be objects: {reference}"
            )
        return constructor, arguments

    @staticmethod
    def _validate_arguments(
        callable_object: Callable[..., object],
        arguments: dict[str, object],
        reference: str,
    ) -> None:
        try:
            inspect.signature(callable_object).bind(**arguments)
        except TypeError as error:
            raise BotModeError(f"Invalid Campaign parameters for {reference}: {error}") from error

    @staticmethod
    def _validate_generator(callable_object: Callable[..., object], reference: str) -> None:
        if not inspect.isgeneratorfunction(callable_object):
            raise BotModeError(f"Campaign capability is not a generator: {reference}")

    @staticmethod
    def _internal_module(module_name: str, reference: str) -> Any:
        if not any(
            module_name == prefix or module_name.startswith(f"{prefix}.")
            for prefix in _ALLOWED_MODULES
        ):
            raise BotModeError(f"Campaign module is not allowed: {reference}")
        try:
            return import_module(module_name)
        except ImportError as error:
            raise BotModeError(f"Campaign module cannot be loaded: {reference}") from error

    def _resolve_value(
        self,
        value: object,
        step: MissionStep,
        rules: Mapping[str, object],
    ) -> object:
        if isinstance(value, str) and value.startswith("$"):
            return self._binding(value[1:], step, rules)
        if isinstance(value, list):
            return [self._resolve_value(item, step, rules) for item in value]
        if isinstance(value, dict):
            return {
                key: self._resolve_value(item, step, rules)
                for key, item in value.items()
            }
        return value

    def _binding(
        self,
        path: str,
        step: MissionStep,
        rules: Mapping[str, object],
    ) -> object:
        root, dot, remainder = path.partition(".")
        if root == "step":
            current: object = step
        elif root == "rules":
            if not dot or remainder not in rules:
                raise BotModeError(f"Unknown Campaign parameter binding: ${path}")
            return rules[remainder]
        elif root in self._bindings:
            current = self._bindings[root]
        else:
            raise BotModeError(f"Unknown Campaign parameter binding: ${path}")

        for segment in remainder.split(".") if dot else ():
            if isinstance(current, Mapping):
                if segment not in current:
                    raise BotModeError(f"Unknown Campaign parameter binding: ${path}")
                current = current[segment]
            else:
                if segment.startswith("_") or not hasattr(current, segment):
                    raise BotModeError(f"Unknown Campaign parameter binding: ${path}")
                current = getattr(current, segment)
        return current
