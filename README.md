# Rubiks2x2x2-OptimalSolver
## Overview
This project presents an optimal solver for the 2x2x2 Rubik's cube, computing all optimal (shortest) solving maneuvers. The computation time is negligible. The solver exclusively utilizes moves of the U, R, and F faces, as the DBL-corner remains fixed. The cube's color scheme is automatically detected.   
## Usage
Upon the initial run, a pruning table is created, requiring approximately 4 MB of disk space. The creation process takes anywhere from less than a minute to a couple of minutes, contingent on the hardware. Typically, you initiate the cube-solving server, which listens on a port of your choice, accepting the cube definition string and returning the solving maneuver. The module example.py provides detailed examples on how to commence the server and utilize a simple GUI interface that interacts seamlessly with the server.   
Execute the example file using "python example.py" or eventually "python3 example.py"

Ensure that you are using Python 3.

![](gui_client.jpg "")

## Search-loop optimization

The solver now precompiles the six legal continuations for each previous move
instead of iterating over all nine moves and rejecting three same-face moves at
every non-root node. This changes only how the existing same-face rule is
executed: the solver still returns every optimal maneuver and its public API is
unchanged.

Run the deterministic benchmark with:

```bash
python3 benchmark_continuations.py \
    --samples 10000 --repeats 5 --verify-samples 1000
```

Move- and pruning-table startup is excluded. Before timing, the benchmark
checks that the optimized and original loops return exactly the same optimal
solutions for every verification state.

On the development host with Python 3.12.3, a deterministic 100,000-state
sample with seven repeats gave these median search times:

- original loop: 4.075 s;
- precompiled continuations: 2.338 s;
- runtime reduction: 42.63%, or 1.743x speed-up.

Both modes returned the same aggregate 405,363 optimal solutions, and exact
solution-set equality was checked on 10,000 states before timing.

The continuation-table regression tests run with:

```bash
python3 -m unittest test_continuations.py
```


