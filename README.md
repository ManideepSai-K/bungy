# Bungy
A browser-based Mars rover exploration simulator by K. Manideep Sai.

**[Open the simulator](https://manideepsai-k.github.io/bungy/)**

## Use
1. Choose a terrain seed and start / destination.
2. Set vehicle limits and planning budgets; select **Compare routes**.
3. Select a successful route card and drive. Pause to inspect, or reset & compare.
4. Switch map layers to inspect estimated slope or observer-only ground truth.

## Navigation
Three independent searches start from identical terrain knowledge and vehicle constraints:
- Distance A*: shortest four-connected grid route.
- Terrain A*: minimizes a designed slope/relief score.
- Quick: weighted A* (heuristic weight 2); may reduce search effort at a cost in route quality.
Quick is not guaranteed faster. The planners can choose the same route.

Safety checks cover map boundaries, swept circular rock clearance, maximum local slope,
and a geometric terrain-relief proxy for ground clearance. Unsafe edges are rejected.
Scores are **not energy, probabilities or real rover telemetry**.

Each planner has a wall-clock search cap and expansion cap. Search time excludes
height/slope setup; total comparison time includes it. This is not a hard real-time system.
Time-budget results vary by device; expansion budgets support reproducible experiments.

Terrain/quick searches prune prefixes above the remaining score cap. Distance search
rejects its returned candidate if its terrain score exceeds that cap; it does **not**
solve the resource-constrained shortest-path problem or prove no other acceptable route exists.
Exhausted search, score rejection, time exhaustion and expansion exhaustion are separate outcomes.

## Terrain and sensing
A seed generates smooth sinusoidal terrain, crater bowls/rims and clustered circular rocks.
Small Gaussian depressions are omitted from the initial mapping product. The 4 m idealized
local sensor replaces nearby estimated heights with ground truth. Driving rechecks the route,
stops to replan on hazards, and enforces the remaining mission score budget.
A simulator-only truth guard stops a move if it would cross a missed hazard.
This prevents simulated damage; it is not sensing available to the planner.

At most 20 replans are allowed. There is no wheel/soil interaction, wheel sinkage,
vehicle dynamics, noisy sensing, articulated suspension, or prediction of actual entrapment.
The raster is 1 metre; smaller features cannot be resolved faithfully.

Ground clearance uses the elevation residual range relative to a local tangent plane
over a conservative swept bounding box. This is a teaching proxy, **not ACE**.
Surface and gradient approximations are not guarantees about continuous physical terrain.

## Score
For each 1 m move:
`score = distance * (1 + 3*(slope/slope_limit)^2 + relief/clearance)`.
Both routes are measured by distance and the same terrain score. Executed score uses
the simulation's true surface, so it can differ from the initially predicted score.

## Development
Python 3:
```sh
python -m http.server 8000
python -m unittest -v
```
Open http://localhost:8000. No pip/npm installation is required.
Pinned Pyodide 0.29.4 loads from jsDelivr and executes Python in a Web Worker.
GitHub Pages serves the main branch root. Python tests run through GitHub Actions.

- `simulator.py`: terrain, geometry, three planners, persistent mission state
- `app.js`: controls, map overlays, animation and mission log
- `worker.js`: Python worker bridge and error reporting
- `planner.py`: original binary-grid baseline, retained with regression tests

## References
- [NASA/JPL path-ranking research](https://ntrs.nasa.gov/citations/20220003784)
- [NASA AutoNav mapping](https://science.nasa.gov/resource/computer-simulation-of-perseverances-first-autonav-drive/)
- [ACE original paper](https://onlinelibrary.wiley.com/doi/abs/10.1002/rob.21892)
- [JPL AEGIS](https://superintelligence.jpl.nasa.gov/public/projects/aegis/)
- [Power of Ten](https://www.spinroot.com/p10/)

Educational software with synthetic measurements. Not NASA flight software.

