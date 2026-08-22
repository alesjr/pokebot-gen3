from collections import deque
from dataclasses import dataclass
from typing import Generator, TypeAlias

from modules.context import context
from modules.map import MapWarp, get_map_data
from modules.map_data import MapFRLG, MapRSE, get_map_enum
from modules.map_path import PathFindingError, calculate_path
from modules.modes._interface import BotModeError
from modules.modes.util.walking import navigate_to
from modules.player import get_player_location


MapId: TypeAlias = tuple[int, int]
MapEnum: TypeAlias = MapFRLG | MapRSE


@dataclass(frozen=True)
class _WarpStep:
    source_map: MapId
    coordinates: tuple[int, int]
    destination_map: MapId


class Navigator:
    """High-level navigation through connected maps, doors, caves, and stairs."""

    def go_to(
        self,
        destination_map: MapId | MapEnum,
        coordinates: tuple[int, int],
        *,
        run: bool = True,
        avoid_encounters: bool = True,
        avoid_scripted_events: bool = True,
    ) -> Generator:
        """Find current location, leave enclosing maps, then reach destination."""
        destination = self._normalise_map(destination_map)

        while True:
            current_map, current_coordinates = get_player_location()
            current = self._normalise_map(current_map)
            if current == destination and current_coordinates == coordinates:
                return

            if self._maps_are_walk_connected(current, destination):
                yield from navigate_to(
                    destination,
                    coordinates,
                    run=run,
                    avoid_encounters=avoid_encounters,
                    avoid_scripted_events=avoid_scripted_events,
                )
                return

            warp = self._find_next_warp(current, current_coordinates, destination)
            if warp is None:
                raise BotModeError(
                    f"No route from {get_map_enum(current).name} to {get_map_enum(destination).name}."
                )

            yield from navigate_to(
                warp.source_map,
                warp.coordinates,
                run=run,
                avoid_encounters=avoid_encounters,
                avoid_scripted_events=avoid_scripted_events,
            )

            new_map, _ = get_player_location()
            if self._normalise_map(new_map) == current:
                raise BotModeError(
                    f"Warp at {warp.coordinates} @ {get_map_enum(current).name} did not change maps."
                )

    def leave_and_go_to(
        self,
        destination_map: MapId | MapEnum,
        coordinates: tuple[int, int],
        **options,
    ) -> Generator:
        """Explicit alias for callers that want to describe leaving before travelling."""
        yield from self.go_to(destination_map, coordinates, **options)

    def _find_next_warp(
        self,
        current_map: MapId,
        current_coordinates: tuple[int, int],
        destination_map: MapId,
    ) -> _WarpStep | None:
        components, component_by_map = self._build_walk_components()
        current_component = component_by_map[current_map]
        destination_component = component_by_map[destination_map]
        warps_by_component = {
            index: self._component_warps(component, component_by_map)
            for index, component in enumerate(components)
        }
        reverse_edges: dict[int, set[int]] = {index: set() for index in range(len(components))}
        for source_component, warps in warps_by_component.items():
            for warp in warps:
                reverse_edges[component_by_map[warp.destination_map]].add(source_component)

        distance_to_destination = {destination_component: 0}
        queue = deque([destination_component])
        while queue:
            component = queue.popleft()
            for predecessor in reverse_edges[component]:
                if predecessor not in distance_to_destination:
                    distance_to_destination[predecessor] = distance_to_destination[component] + 1
                    queue.append(predecessor)

        if current_component not in distance_to_destination:
            return None

        next_distance = distance_to_destination[current_component] - 1
        candidates = [
            warp
            for warp in warps_by_component[current_component]
            if distance_to_destination.get(component_by_map[warp.destination_map]) == next_distance
        ]

        reachable: list[tuple[int, _WarpStep]] = []
        for first in candidates:
            try:
                path = calculate_path(
                    (current_map, current_coordinates),
                    (first.source_map, first.coordinates),
                )
            except PathFindingError:
                continue
            reachable.append((len(path), first))

        return min(reachable, key=lambda candidate: candidate[0])[1] if reachable else None

    def _build_walk_components(self) -> tuple[list[set[MapId]], dict[MapId, int]]:
        maps = {
            self._normalise_map(map_enum)
            for map_enum in self._map_enum()
            if not context.rom.is_rs or map_enum.exists_on_rs
        }
        neighbours: dict[MapId, set[MapId]] = {map_id: set() for map_id in maps}
        for map_id in maps:
            for connection in get_map_data(map_id, (0, 0)).connections:
                destination = (connection.destination_map_group, connection.destination_map_number)
                if destination in maps:
                    neighbours[map_id].add(destination)
                    neighbours[destination].add(map_id)

        components: list[set[MapId]] = []
        component_by_map: dict[MapId, int] = {}
        for map_id in maps:
            if map_id in component_by_map:
                continue
            component_index = len(components)
            component = set()
            queue = deque([map_id])
            component_by_map[map_id] = component_index
            while queue:
                member = queue.popleft()
                component.add(member)
                for neighbour in neighbours[member]:
                    if neighbour not in component_by_map:
                        component_by_map[neighbour] = component_index
                        queue.append(neighbour)
            components.append(component)
        return components, component_by_map

    def _component_warps(
        self, component: set[MapId], component_by_map: dict[MapId, int]
    ) -> list[_WarpStep]:
        result = []
        source_component = component_by_map[next(iter(component))]
        for source_map in component:
            for warp in get_map_data(source_map, (0, 0)).warps:
                try:
                    destination = self._warp_destination(warp)
                except (IndexError, ValueError):
                    continue
                if destination in component_by_map and component_by_map[destination] != source_component:
                    result.append(_WarpStep(source_map, warp.local_coordinates, destination))
        return result

    def _maps_are_walk_connected(self, source: MapId, destination: MapId) -> bool:
        _, component_by_map = self._build_walk_components()
        return component_by_map[source] == component_by_map[destination]

    @staticmethod
    def _warp_destination(warp: MapWarp) -> MapId:
        destination = warp.destination_location
        return destination.map_group_and_number

    @staticmethod
    def _normalise_map(map_id: MapId | MapEnum) -> MapId:
        return map_id if isinstance(map_id, tuple) else map_id.value

    @staticmethod
    def _map_enum() -> type[MapFRLG] | type[MapRSE]:
        return MapRSE if context.rom.is_rse else MapFRLG
