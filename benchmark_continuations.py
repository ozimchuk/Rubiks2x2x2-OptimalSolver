"""Benchmark precompiled continuations against the original search loop."""

import argparse
import contextlib
import json
import random
import statistics
import sys
import time

with contextlib.redirect_stdout(sys.stderr):
    import solver
    import defs
    import enums as en
    import moves as mv
    import pruning as pr


baseline_solutions = []


def baseline_search(cornperm, corntwist, sofar, togo):
    """The original solver.search implementation."""
    if togo == 0:
        baseline_solutions.append(sofar[:])
        return

    for move in en.Move:
        if len(sofar) > 0 and sofar[-1] // 3 == move // 3:
            continue

        cornperm_new = mv.cornperm_move[9 * cornperm + move]
        corntwist_new = mv.corntwist_move[9 * corntwist + move]
        if pr.corner_depth[
                defs.N_TWIST * cornperm_new + corntwist_new] >= togo:
            continue

        sofar.append(move)
        baseline_search(cornperm_new, corntwist_new, sofar, togo - 1)
        sofar.pop()


def enumerate_state(state_id, optimized):
    global baseline_solutions
    cornperm, corntwist = divmod(state_id, defs.N_TWIST)
    depth = pr.corner_depth[state_id]
    if optimized:
        solver.solutions = []
        solver.search(cornperm, corntwist, [], depth)
        return solver.solutions

    baseline_solutions = []
    baseline_search(cornperm, corntwist, [], depth)
    return baseline_solutions


def verify(states):
    for state_id in states:
        baseline = {
            tuple(solution)
            for solution in enumerate_state(state_id, optimized=False)
        }
        optimized = {
            tuple(solution)
            for solution in enumerate_state(state_id, optimized=True)
        }
        if optimized != baseline:
            raise AssertionError(
                'solution mismatch for state ' + str(state_id))


def timed_run(states, optimized):
    started = time.perf_counter()
    solution_count = 0
    for state_id in states:
        solution_count += len(enumerate_state(state_id, optimized))
    return time.perf_counter() - started, solution_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=10_000)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--seed', type=int, default=20261024)
    parser.add_argument('--verify-samples', type=int, default=1_000)
    args = parser.parse_args()

    state_count = defs.N_CORNERS * defs.N_TWIST
    if not 1 <= args.samples < state_count:
        parser.error('--samples must be in 1..3,674,159')
    states = random.Random(args.seed).sample(
        range(1, state_count), args.samples)
    verify_count = min(args.verify_samples, len(states))
    verify(states[:verify_count])

    warm_count = min(100, len(states))
    timed_run(states[:warm_count], optimized=False)
    timed_run(states[:warm_count], optimized=True)

    timings = {False: [], True: []}
    solution_counts = {}
    for repeat in range(args.repeats):
        modes = (False, True) if repeat % 2 == 0 else (True, False)
        for optimized in modes:
            elapsed, count = timed_run(states, optimized)
            timings[optimized].append(elapsed)
            solution_counts[optimized] = count

    if solution_counts[False] != solution_counts[True]:
        raise AssertionError('aggregate solution counts differ')
    baseline_time = statistics.median(timings[False])
    optimized_time = statistics.median(timings[True])
    result = {
        'schema': 1,
        'states': len(states),
        'repeats': args.repeats,
        'verified_states': verify_count,
        'solutions': solution_counts[True],
        'baseline': {
            'median_seconds': baseline_time,
            'all_seconds': timings[False],
        },
        'precompiled_continuations': {
            'median_seconds': optimized_time,
            'all_seconds': timings[True],
        },
        'runtime_reduction_fraction': 1.0 - optimized_time / baseline_time,
        'speedup': baseline_time / optimized_time,
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
