# Rubiks2x2x2-OptimalSolver
## Overview
This project presents an optimal solver for the 2x2x2 Rubik's cube, computing all optimal (shortest) solving maneuvers. The computation time is negligible. The solver exclusively utilizes moves of the U, R, and F faces, as the DBL-corner remains fixed. The cube's color scheme is automatically detected.   
## Usage
Upon the initial run, a pruning table is created, requiring approximately 4 MB of disk space. The creation process takes anywhere from less than a minute to a couple of minutes, contingent on the hardware. Typically, you initiate the cube-solving server, which listens on a port of your choice, accepting the cube definition string and returning the solving maneuver. The module example.py provides detailed examples on how to commence the server and utilize a simple GUI interface that interacts seamlessly with the server.   
Execute the example file using "python example.py" or eventually "python3 example.py"

Ensure that you are using Python 3.

![](gui_client.jpg "")

## Certified geodesic-language pruning

This fork adds an optional finite-memory language that rejects 36 length-4
move motifs. Its minimal DFA has 47 states; the recursive hot path uses
equivalent precompiled continuation tables. The rule was derived from all
14,921,182 optimal paths in the fixed-corner 2x2x2 HTM graph and independently
validated on all 3,674,160 states. Every state retains at least one optimal
solution.

The original behavior is unchanged by default:

```python
import solver

all_optimal = solver.solve(cubestring)
pruned_optimal_subset = solver.solve(
    cubestring, use_geodesic_pruning=True)
```

The pruned mode returns a nonempty subset of the optimal maneuvers, not every
optimal maneuver. Do not enable it when complete solution enumeration is the
goal. On the canonical reduced-word tree through depth 11, the language
removes 11.00253% of cumulative nodes.

Run the deterministic wall-clock and search-node benchmark with:

```bash
python3 benchmark_geodesic_pruning.py \
    --samples 10000 --repeats 5 --verify-samples 1000
```

The benchmark excludes move/pruning-table startup time, alternates mode order
between repeats, and verifies that every pruned result is a nonempty subset of
the upstream result before timing. Use `--all` to benchmark all non-solved
states.

On the development host with Python 3.12.3, a deterministic 100,000-state
sample with five repeats gave these medians:

- upstream-equivalent search: 4.072 s;
- precompiled same-face pruning only: 2.281 s;
- same-face plus the new motif language: 2.462 s.

The motif language reduced actual search calls by 0.832% and coordinate-table
lookups by 1.341%. It was 7.93% slower than the optimized same-face-only
ablation because Python context tracking costs more than the saved exact-depth
lookups. The complete implementation was 1.654x faster than the literal
upstream loop, but that gain comes from compiling the existing same-face rule,
not from the exotic motifs. Thus, the exact 11.00253% abstract-tree reduction
does **not** become an 11% runtime improvement in this solver.

The language certificate and minimal DFA construction are in
`geodesic_pruning.py`; exact language-count regression tests are in
`test_geodesic_pruning.py`.


