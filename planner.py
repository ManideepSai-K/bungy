"""Bungy lesson 1: bounded A* on a fully known binary occupancy grid."""
import heapq
import json
import time

def plan(grid, start, goal, max_expansions=4096):
    """Coordinates are [column, row]; 1 means blocked; one cell is one metre."""
    began = time.perf_counter()
    def result(status, path=None, expanded=0):
        path = path or []
        return dict(status=status, path=path, expanded=expanded,
                    distance_m=max(0, len(path)-1) if status == "SUCCESS" else None,
                    planning_ms=(time.perf_counter()-began)*1000)
    if (not isinstance(grid, list) or not 1 <= len(grid) <= 64
            or not all(isinstance(row, list) for row in grid)):
        return result("INVALID_MAP")
    width = len(grid[0])
    if not 1 <= width <= 64 or any(len(row) != width for row in grid):
        return result("INVALID_MAP")
    if any(type(v) is not int or v not in (0, 1) for row in grid for v in row):
        return result("INVALID_MAP")
    if type(max_expansions) is not int or not 1 <= max_expansions <= 4096:
        return result("INVALID_BUDGET")
    for label, point in (("START", start), ("GOAL", goal)):
        if (not isinstance(point, (list, tuple)) or len(point) != 2
                or any(type(v) is not int for v in point)):
            return result("INVALID_" + label)
        x, y = point
        if not (0 <= x < width and 0 <= y < len(grid)):
            return result(label + "_OUT_OF_BOUNDS")
        if grid[y][x]:
            return result(label + "_BLOCKED")
    start, goal = tuple(start), tuple(goal)
    def heuristic(point):
        return abs(point[0]-goal[0]) + abs(point[1]-goal[1])
    frontier = [(heuristic(start), 0, start)]
    costs, parents, closed = {start: 0}, {}, set()
    # Each expanded cell inserts at most four entries; bound stale entries too.
    for _ in range(4 * width * len(grid) + 1):
        if not frontier:
            return result("NO_ROUTE", expanded=len(closed))
        _, cost, current = heapq.heappop(frontier)
        if current in closed:
            continue
        if current == goal:
            path = [current]
            for _ in range(width * len(grid)):
                if path[-1] == start:
                    return result("SUCCESS", list(reversed(path)), len(closed))
                path.append(parents[path[-1]])
            return result("INTERNAL_ERROR")
        if len(closed) >= max_expansions:
            return result("BUDGET_EXCEEDED", expanded=len(closed))
        closed.add(current)
        x, y = current
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            nxt = (x+dx, y+dy)
            nx, ny = nxt
            if not (0 <= nx < width and 0 <= ny < len(grid)) or grid[ny][nx]:
                continue
            candidate = cost + 1
            if candidate < costs.get(nxt, float("inf")):
                costs[nxt], parents[nxt] = candidate, current
                heapq.heappush(frontier, (candidate+heuristic(nxt), candidate, nxt))
    return result("INTERNAL_ERROR", expanded=len(closed))

def plan_json(payload):
    try:
        request = json.loads(payload)
        return json.dumps(plan(request["grid"], request["start"], request["goal"]))
    except (ValueError, KeyError, TypeError):
        return json.dumps({"status": "INVALID_REQUEST", "path": []})
