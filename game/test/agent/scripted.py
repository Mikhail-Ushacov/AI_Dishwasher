from collections import deque
from typing import List, Set, Tuple

ACTION_UP = 0
ACTION_DOWN = 1
ACTION_LEFT = 2
ACTION_RIGHT = 3
ACTION_INTERACT = 4
ACTION_INTERACT_SEC = 5
ACTION_WAIT = 6

_DIR = [(0, -1), (0, 1), (-1, 0), (1, 0)]
_FACINGS = ["up", "down", "left", "right"]
_PLAYER_TO_FACING_TILE = {
    ACTION_UP: (0, -1),
    ACTION_DOWN: (0, 1),
    ACTION_LEFT: (-1, 0),
    ACTION_RIGHT: (1, 0),
}


def bfs(level, start, targets: Set[Tuple[int, int]]):
    if start in targets:
        return []
    q = deque()
    q.append((start[0], start[1], []))
    visited = {start}
    while q:
        x, y, path = q.popleft()
        for dx, dy, act in [(0, -1, ACTION_UP), (0, 1, ACTION_DOWN),
                             (-1, 0, ACTION_LEFT), (1, 0, ACTION_RIGHT)]:
            nx, ny = x + dx, y + dy
            if (nx, ny) in targets:
                return path + [act]
            if (nx, ny) not in visited and level.can_move(nx, ny):
                visited.add((nx, ny))
                q.append((nx, ny, path + [act]))
    return []


def facing_action(from_cell, to_cell) -> int:
    dx = to_cell[0] - from_cell[0]
    dy = to_cell[1] - from_cell[1]
    if dx > 0: return ACTION_RIGHT
    if dx < 0: return ACTION_LEFT
    if dy > 0: return ACTION_DOWN
    if dy < 0: return ACTION_UP
    return ACTION_WAIT


def is_facing(player, face_action) -> bool:
    return player.facing == _FACINGS[face_action] if face_action < 4 else False


def _end_of(path, start):
    x, y = start
    for a in path:
        dx, dy = _DIR[a]
        x += dx; y += dy
    return (x, y)


def find_interaction_spots(level, station_name):
    """Return list of (px, py, face_act) where player can interact with station_name."""
    ts = level.tile_size
    spots = []
    for obj in level.interactive_objects:
        if obj["name"] != station_name:
            continue
        r = obj["rect"]
        for px in range(level.width_in_tiles):
            for py in range(level.height_in_tiles):
                if not level.can_move(px, py):
                    continue
                for face_act, (fdx, fdy) in enumerate(_DIR):
                    tx = px + fdx
                    ty = py + fdy
                    if 0 <= tx < level.width_in_tiles and 0 <= ty < level.height_in_tiles:
                        cp = (tx * ts + ts // 2, ty * ts + ts // 2)
                        if r.collidepoint(cp):
                            spots.append((px, py, face_act))
    return spots


class ScriptedAgent:
    def __init__(self, auto_interact: bool = False):
        self._spot_cache = {}
        self.auto_interact = auto_interact

    def _spots(self, level, name):
        if name not in self._spot_cache:
            self._spot_cache[name] = find_interaction_spots(level, name)
        return self._spot_cache[name]

    def _navigate_raw(self, player, level, station_name, interact_action):
        """Return list of actions to reach + interact with station (7-action space)."""
        px, py = player.cell_x, player.cell_y
        spots = self._spots(level, station_name)
        if not spots:
            return [ACTION_WAIT]

        best_path = None
        best_spot = None
        for spx, spy, sface in spots:
            p = bfs(level, (px, py), {(spx, spy)})
            if p is not None and (best_path is None or len(p) < len(best_path)):
                best_path = p
                best_spot = (spx, spy, sface)

        if best_spot is None:
            return [ACTION_WAIT]

        spx, spy, sface = best_spot

        if (px, py) == (spx, spy):
            if is_facing(player, sface):
                return [interact_action]
            return [sface, interact_action]

        if best_path:
            return best_path + [sface, interact_action]
        return [ACTION_WAIT]

    def _navigate_auto(self, player, level, station_name):
        """Return list of actions to reach + face station (5-action auto_interact mode)."""
        px, py = player.cell_x, player.cell_y
        spots = self._spots(level, station_name)
        if not spots:
            return [ACTION_WAIT]

        # Group spots by tile position
        pos_to_facings = {}
        for spx, spy, sface in spots:
            pos_to_facings.setdefault((spx, spy), []).append(sface)

        best_path = None
        best_pos = None
        best_facing = None
        for (spx, spy), facings in pos_to_facings.items():
            p = bfs(level, (px, py), {(spx, spy)})
            if p is not None and (best_path is None or len(p) < len(best_path)):
                best_path = p
                best_pos = (spx, spy)
                # Choose facing: prefer already-facing, otherwise pick first
                for f in facings:
                    if (px, py) == (spx, spy) and is_facing(player, f):
                        best_facing = f
                        break
                if best_facing is None:
                    best_facing = facings[0]

        if best_pos is None:
            return [ACTION_WAIT]

        spx, spy = best_pos

        if (px, py) == (spx, spy):
            if best_facing is not None and is_facing(player, best_facing):
                return [ACTION_WAIT]
            return [best_facing, ACTION_WAIT]

        if best_path:
            return best_path + [best_facing, ACTION_WAIT]
        return [ACTION_WAIT]

    def get_actions(self, player, kitchen, level) -> List[int]:
        held = player.held_item
        if held is None:
            target, interact_act = "fridge", ACTION_INTERACT
        else:
            state = held.state
            if state == "raw":
                target, interact_act = "sink", ACTION_INTERACT
            elif state == "washed":
                if kitchen.current_order == "baked":
                    target, interact_act = "cooking_place", ACTION_INTERACT_SEC
                else:
                    target, interact_act = "table", ACTION_INTERACT
            elif state == "cut":
                target, interact_act = "cooking_place", ACTION_INTERACT
            elif state in ("fried", "baked"):
                target, interact_act = "order", ACTION_INTERACT
            else:
                return [ACTION_WAIT]

        if self.auto_interact:
            return self._navigate_auto(player, level, target)
        return self._navigate_raw(player, level, target, interact_act)
