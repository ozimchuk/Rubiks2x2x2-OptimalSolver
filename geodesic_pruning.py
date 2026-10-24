"""Certified finite-memory pruning for optimal 2x2x2 HTM searches.

The forbidden motifs below were found by exhaustive analysis of all 14,921,182
optimal paths in the fixed-corner 2x2x2 graph.  The complete set is closed
under permutations of the U/R/F axes and reverse-inverse.  Exhaustive
product-DAG validation proves that every one of the 3,674,160 states retains
at least one optimal path.

This language removes 11.0025304934% of the cumulative canonical reduced-word
tree through depth 11.  It deliberately retains only a complete subset of
optimal paths, so it must not be enabled when a caller requests *all* optimal
maneuvers.
"""

from enums import Move


MEMORY = 3
MOVE_COUNT = 9

# Move encoding agrees with enums.Move:
# U, U2, U', R, R2, R', F, F2, F'.
FORBIDDEN_MOTIFS = frozenset(
    {
        337,
        338,
        583,
        584,
        1065,
        1066,
        1067,
        1311,
        1312,
        1313,
        1795,
        2041,
        2305,
        2306,
        2797,
        2798,
        3033,
        3034,
        3035,
        3525,
        3526,
        3527,
        3763,
        4255,
        4519,
        4520,
        4765,
        4766,
        5247,
        5248,
        5249,
        5493,
        5494,
        5495,
        5977,
        6223,
    }
)

# Hot-path form: for each three-move prefix, a nine-bit mask identifies
# forbidden fourth moves. This is equivalent to the DFA but avoids a Python
# function call for every candidate move in the recursive solver.
_forbidden_next_masks = [0] * (MOVE_COUNT ** MEMORY)
for _motif in FORBIDDEN_MOTIFS:
    _forbidden_next_masks[_motif // MOVE_COUNT] |= 1 << (_motif % MOVE_COUNT)
FORBIDDEN_NEXT_MASKS = tuple(_forbidden_next_masks)
REDUCED_NEXT_MOVES = tuple(
    tuple(
        move
        for move in Move
        if move // 3 != previous // 3
    )
    for previous in range(MOVE_COUNT)
)
ALLOWED_NEXT_MOVES = tuple(
    tuple(
        move
        for move in REDUCED_NEXT_MOVES[prefix % MOVE_COUNT]
        if not (FORBIDDEN_NEXT_MASKS[prefix] & (1 << move))
    )
    for prefix in range(MOVE_COUNT ** MEMORY)
)
NEXT_CONTEXT = tuple(
    tuple((prefix % (MOVE_COUNT ** (MEMORY - 1))) * MOVE_COUNT + move
          for move in range(MOVE_COUNT))
    for prefix in range(MOVE_COUNT ** MEMORY)
)


def _encode(moves):
    code = 0
    for move in moves:
        code = code * MOVE_COUNT + move
    return code


def _compile_minimal_dfa():
    """Build and minimize the suffix automaton once at module import."""
    contexts = [()]
    frontier = [()]
    for _ in range(MEMORY):
        next_frontier = []
        for context in frontier:
            choices = range(MOVE_COUNT)
            if context:
                choices = (
                    move
                    for move in choices
                    if move // 3 != context[-1] // 3
                )
            for move in choices:
                next_frontier.append(context + (move,))
        contexts.extend(next_frontier)
        frontier = next_frontier

    index = {context: state for state, context in enumerate(contexts)}
    dead = len(contexts)
    transitions = [[dead] * MOVE_COUNT for _ in range(dead + 1)]

    for state, context in enumerate(contexts):
        for move in range(MOVE_COUNT):
            if context and context[-1] // 3 == move // 3:
                continue
            if (
                len(context) == MEMORY
                and _encode(context + (move,)) in FORBIDDEN_MOTIFS
            ):
                continue
            next_context = (context + (move,))[-MEMORY:]
            transitions[state][move] = index[next_context]

    blocks = [0] * (dead + 1)
    blocks[dead] = 1
    while True:
        signature_ids = {}
        refined = []
        for state, targets in enumerate(transitions):
            signature = (
                state != dead,
                *(blocks[target] for target in targets),
            )
            refined.append(
                signature_ids.setdefault(signature, len(signature_ids))
            )
        if refined == blocks:
            break
        blocks = refined

    block_count = max(blocks) + 1
    representatives = [None] * block_count
    for state, block in enumerate(blocks):
        representatives[block] = state
    minimized = tuple(
        tuple(blocks[target] for target in transitions[state])
        for state in representatives
    )
    return minimized, blocks[0], blocks[dead]


TRANSITIONS, START_STATE, DEAD_STATE = _compile_minimal_dfa()
DFA_STATE_COUNT = len(TRANSITIONS)


def transition(state, move):
    """Return the next DFA state; ``DEAD_STATE`` means the move is forbidden."""
    return TRANSITIONS[state][move]


assert len(FORBIDDEN_MOTIFS) == 36
assert DFA_STATE_COUNT == 47
