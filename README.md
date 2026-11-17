# bungy
A Mars-inspired rover mission lab by K. Manideep Sai.

## First runnable slice
A fixed synthetic 12 × 12 occupancy grid, clickable or keyboard-entered endpoints,
bounded Python A*, and rover animation. Four-direction motion, 1 metre per cell.
The rover is a point in this lesson. No width, slope, physics, sensing or terrain
cost model is implemented yet. This is not NASA flight software or ACE.

## Run locally
Install Python 3, open a terminal in this repository, then run:
```sh
python -m http.server 8000
```
Open http://localhost:8000. Internet access is needed to load pinned Pyodide
0.29.4 from jsDelivr. Python runs in a Web Worker; no backend service is needed.
Do not open index.html directly as a file.

## Test
```sh
python -m unittest -v
```
Timing measures the Python planning call only, not runtime loading or drawing.
Search expansion limits and a browser watchdog report budget/timeout failures
separately from an exhausted search with no route.

## Learn through experiments
1. Click Plan route, then Drive route. Follow the highlighted path through the gap.
2. Check Seal the passage. Predict the result, then plan again.
3. Place both endpoints on the same side of the sealed wall. Why is a route possible?
4. In planner.py, find heuristic(): |x-goal_x| + |y-goal_y| is Manhattan distance.
   For (1,9) to (10,2), its value is 16. Each legal move costs 1.
5. Change the heuristic to return 0 and rerun tests. This makes the search Dijkstra's;
   compare expanded cells, without assuming timing from one tiny run is reliable.

## Next steps
- Seeded smooth terrain, mathematical craters and rock clusters.
- Circular footprint and swept-movement clearance, maximum slope.
- Distance and terrain-cost objectives under identical safety constraints.
- Limited sensing and replanning; held-out-terrain ML evaluation.
- AEGIS-inspired explicit science criteria; delayed communications and coding.
- Stereo depth as an alternative terrain-map source.

## Technical references
- [NASA AutoNav height maps](https://science.nasa.gov/resource/computer-simulation-of-perseverances-first-autonav-drive/)
- [ACE original paper](https://onlinelibrary.wiley.com/doi/abs/10.1002/rob.21892)
- [JPL AEGIS](https://superintelligence.jpl.nasa.gov/public/projects/aegis/)
- [Power of Ten](https://www.spinroot.com/p10/)
- [Pyodide](https://pyodide.org/en/0.29.4/usage/index.html)

## Static deployment
Compatible with GitHub Pages: Settings → Pages → Deploy from a branch → main → / (root).
Enabling Pages is a separate hosting setting; committing these files does not enable it.
