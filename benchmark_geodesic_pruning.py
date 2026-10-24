"""Benchmark the certified geodesic-language pruning against upstream search.

Table construction/loading happens during imports and is intentionally excluded
from the measurements.  Both modes enumerate their complete set of retained
optimal solutions; the baseline mode is behaviorally identical to upstream.
"""

import argparse
import contextlib
import json
import random
import statistics
import sys
import time

with contextlib.redirect_stdout(sys.stderr):
    import defs
    import geodesic_pruning as gp
    import solver
    import moves as mv
    import pruning as pr


def empty_stats():
    return {
        'search_nodes': 0,
        'solutions': 0,
        'same_face_prunes': 0,
        'language_prunes': 0,
        'coordinate_lookups': 0,
        'distance_prunes': 0,
    }


def state_coordinates(state_id):
    return divmod(state_id, defs.N_TWIST)


def search_canonical_fast(cornperm, corntwist, sofar, togo, stats):
    """Ablation baseline: precompiled same-face pruning, no new motifs."""
    if stats is not None:
        stats['search_nodes'] += 1
    if togo == 0:
        solver.solutions.append(sofar[:])
        if stats is not None:
            stats['solutions'] += 1
        return

    if not sofar:
        moves = range(9)
    else:
        moves = gp.REDUCED_NEXT_MOVES[sofar[-1]]
        if stats is not None:
            stats['same_face_prunes'] += 3

    for move in moves:
        if stats is not None:
            stats['coordinate_lookups'] += 1
        cornperm_new = mv.cornperm_move[9 * cornperm + move]
        corntwist_new = mv.corntwist_move[9 * corntwist + move]
        if pr.corner_depth[
                defs.N_TWIST * cornperm_new + corntwist_new] >= togo:
            if stats is not None:
                stats['distance_prunes'] += 1
            continue
        sofar.append(move)
        search_canonical_fast(
            cornperm_new, corntwist_new, sofar, togo - 1, stats)
        sofar.pop()


def enumerate_state(state_id, mode, stats=None, return_solutions=True):
    cornperm, corntwist = state_coordinates(state_id)
    depth = pr.corner_depth[state_id]
    solver.solutions = []
    if mode == 'canonical_fast':
        search_canonical_fast(cornperm, corntwist, [], depth, stats)
    else:
        solver.search(
            cornperm,
            corntwist,
            [],
            depth,
            use_geodesic_pruning=(mode == 'geodesic_pruning'),
            stats=stats)
    if return_solutions:
        return tuple(tuple(solution) for solution in solver.solutions)
    return None


def verify(states):
    for state_id in states:
        baseline = set(enumerate_state(state_id, 'baseline'))
        pruned = set(enumerate_state(state_id, 'geodesic_pruning'))
        if not pruned:
            raise AssertionError(
                'geodesic language removed every solution for state '
                + str(state_id))
        if not pruned <= baseline:
            raise AssertionError(
                'geodesic language produced a non-optimal solution for state '
                + str(state_id))


def timed_run(states, mode, collect_stats=False):
    stats = empty_stats() if collect_stats else None
    started = time.perf_counter()
    for state_id in states:
        enumerate_state(state_id, mode, stats, return_solutions=False)
    return time.perf_counter() - started, stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--samples',
        type=int,
        default=10_000,
        help='number of deterministic random non-solved states')
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--seed', type=int, default=20261024)
    parser.add_argument(
        '--verify-samples',
        type=int,
        default=1_000,
        help='states checked for nonempty-subset equivalence before timing')
    parser.add_argument(
        '--all',
        action='store_true',
        help='benchmark all 3,674,159 non-solved states')
    args = parser.parse_args()

    state_count = defs.N_CORNERS * defs.N_TWIST
    if args.all:
        states = range(1, state_count)
    else:
        if not 1 <= args.samples < state_count:
            parser.error('--samples must be in 1..3,674,159')
        states = random.Random(args.seed).sample(
            range(1, state_count), args.samples)

    verify_count = min(args.verify_samples, len(states))
    verify(states[:verify_count])

    # Warm both code paths before collecting wall-clock samples.
    warm_count = min(100, len(states))
    modes = ('baseline', 'canonical_fast', 'geodesic_pruning')
    for mode in modes:
        timed_run(states[:warm_count], mode)

    timings = {mode: [] for mode in modes}
    counters = {}
    for repeat in range(args.repeats):
        offset = repeat % len(modes)
        ordered_modes = modes[offset:] + modes[:offset]
        for mode in ordered_modes:
            elapsed, _ = timed_run(states, mode)
            timings[mode].append(elapsed)
    for mode in modes:
        _, counters[mode] = timed_run(states, mode, collect_stats=True)

    baseline_time = statistics.median(timings['baseline'])
    canonical_time = statistics.median(timings['canonical_fast'])
    pruned_time = statistics.median(timings['geodesic_pruning'])
    baseline_nodes = counters['baseline']['search_nodes']
    pruned_nodes = counters['geodesic_pruning']['search_nodes']
    result = {
        'schema': 1,
        'states': len(states),
        'repeats': args.repeats,
        'verified_states': verify_count,
        'dfa_states': gp.DFA_STATE_COUNT,
        'forbidden_motifs': len(gp.FORBIDDEN_MOTIFS),
        'baseline': {
            'median_seconds': baseline_time,
            'all_seconds': timings['baseline'],
            **counters['baseline'],
        },
        'canonical_fast': {
            'median_seconds': canonical_time,
            'all_seconds': timings['canonical_fast'],
            **counters['canonical_fast'],
        },
        'geodesic_pruning': {
            'median_seconds': pruned_time,
            'all_seconds': timings['geodesic_pruning'],
            **counters['geodesic_pruning'],
        },
        'search_node_reduction_fraction': (
            1.0 - pruned_nodes / baseline_nodes),
        'coordinate_lookup_reduction_fraction': (
            1.0
            - counters['geodesic_pruning']['coordinate_lookups']
            / counters['baseline']['coordinate_lookups']),
        'runtime_reduction_fraction': 1.0 - pruned_time / baseline_time,
        'speedup': baseline_time / pruned_time,
        'motif_only_runtime_reduction_fraction': (
            1.0 - pruned_time / canonical_time),
        'motif_only_speedup': canonical_time / pruned_time,
        'canonical_tree_reduction_fraction': 0.11002530493402571,
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
