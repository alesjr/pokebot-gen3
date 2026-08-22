from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable


class CampaignAction(str, Enum):
    NAVIGATE = "navigate"
    TALK = "talk"
    BATTLE = "battle"
    HEAL = "heal"
    BUY = "buy"
    USE_HM = "use_hm"
    SOLVE_PUZZLE = "solve_puzzle"
    CAPTURE = "capture"
    CREATE_EGG = "create_egg"
    EVOLVE = "evolve"
    TRADE = "trade"
    SAVE = "save"


@dataclass(frozen=True)
class CartridgeSnapshot:
    """Read-only facts sampled from cartridge RAM/save structures."""

    flags: frozenset[str] = frozenset()
    map_name: str | None = None
    inventory: frozenset[str] = frozenset()
    party_species: tuple[str, ...] = ()
    storage_species: frozenset[str] = frozenset()
    game_state: str = "UNKNOWN"


@dataclass(frozen=True)
class CampaignCondition:
    kind: str
    value: str

    def matches(self, snapshot: CartridgeSnapshot) -> bool:
        if self.kind == "flag":
            return self.value in snapshot.flags
        if self.kind == "map":
            return self.value == snapshot.map_name
        if self.kind == "item":
            return self.value in snapshot.inventory
        if self.kind == "party":
            return self.value in snapshot.party_species
        if self.kind == "storage":
            return self.value in snapshot.storage_species
        if self.kind == "game_state":
            return self.value == snapshot.game_state
        raise ValueError(f"unknown campaign condition kind: {self.kind}")


@dataclass(frozen=True)
class CampaignNode:
    mission_id: str
    prerequisites: tuple[str, ...]
    preconditions: tuple[CampaignCondition, ...]
    action: CampaignAction
    completion: tuple[CampaignCondition, ...]
    checkpoint: str
    max_attempts: int

    def __post_init__(self) -> None:
        if not self.completion:
            raise ValueError(f"{self.mission_id}: completion condition required")
        if not self.checkpoint:
            raise ValueError(f"{self.mission_id}: checkpoint required")
        if self.max_attempts < 1:
            raise ValueError(f"{self.mission_id}: max_attempts must be positive")

    def is_complete(self, snapshot: CartridgeSnapshot) -> bool:
        return all(condition.matches(snapshot) for condition in self.completion)

    def is_available(self, snapshot: CartridgeSnapshot, completed: set[str]) -> bool:
        return set(self.prerequisites).issubset(completed) and all(
            condition.matches(snapshot) for condition in self.preconditions
        )


@dataclass
class CampaignRuntime:
    attempts: dict[str, int] = field(default_factory=dict)
    active_mission: str | None = None
    last_checkpoint: str | None = None
    blocked_reason: str | None = None


class CampaignBlocked(RuntimeError):
    pass


class CampaignEngine:
    """Selects work from cartridge truth; runtime history never proves completion."""

    def __init__(
        self,
        nodes: Iterable[CampaignNode],
        handlers: dict[CampaignAction, Callable[[CampaignNode], object]],
        runtime: CampaignRuntime | None = None,
    ):
        self._nodes = tuple(nodes)
        self._by_id = {node.mission_id: node for node in self._nodes}
        if len(self._by_id) != len(self._nodes):
            raise ValueError("duplicate campaign mission id")
        self._validate_graph()
        self._handlers = handlers
        self.runtime = runtime or CampaignRuntime()

    def _validate_graph(self) -> None:
        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(mission_id: str) -> None:
            if mission_id in visiting:
                raise ValueError(f"campaign cycle at {mission_id}")
            if mission_id in visited:
                return
            visiting.add(mission_id)
            for prerequisite in self._by_id[mission_id].prerequisites:
                if prerequisite not in self._by_id:
                    raise ValueError(f"{mission_id}: unknown prerequisite {prerequisite}")
                visit(prerequisite)
            visiting.remove(mission_id)
            visited.add(mission_id)

        for node in self._nodes:
            visit(node.mission_id)

    def reconcile(self, snapshot: CartridgeSnapshot) -> tuple[set[str], CampaignNode | None]:
        completed = {node.mission_id for node in self._nodes if node.is_complete(snapshot)}
        current = next(
            (
                node
                for node in self._nodes
                if node.mission_id not in completed and node.is_available(snapshot, completed)
            ),
            None,
        )
        self.runtime.active_mission = None if current is None else current.mission_id
        if current is None:
            self.runtime.blocked_reason = None if len(completed) == len(self._nodes) else "no_available_mission"
        else:
            self.runtime.blocked_reason = None
        return completed, current

    def start_current(self, snapshot: CartridgeSnapshot) -> object:
        _, node = self.reconcile(snapshot)
        if node is None:
            raise CampaignBlocked(self.runtime.blocked_reason or "campaign complete")
        handler = self._handlers.get(node.action)
        if handler is None:
            self.runtime.blocked_reason = f"missing_action_handler:{node.action.value}"
            raise CampaignBlocked(self.runtime.blocked_reason)
        attempts = self.runtime.attempts.get(node.mission_id, 0) + 1
        self.runtime.attempts[node.mission_id] = attempts
        if attempts > node.max_attempts:
            self.runtime.blocked_reason = f"attempt_limit:{node.mission_id}"
            raise CampaignBlocked(self.runtime.blocked_reason)
        return handler(node)

    def confirm_checkpoint(self, snapshot: CartridgeSnapshot) -> str:
        mission_id = self.runtime.active_mission
        if mission_id is None:
            raise CampaignBlocked("no_active_mission")
        node = self._by_id[mission_id]
        if not node.is_complete(snapshot):
            raise CampaignBlocked(f"completion_not_observed:{mission_id}")
        self.runtime.last_checkpoint = node.checkpoint
        self.runtime.attempts.pop(mission_id, None)
        self.runtime.active_mission = None
        self.runtime.blocked_reason = None
        return node.checkpoint
