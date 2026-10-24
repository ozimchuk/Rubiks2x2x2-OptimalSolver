# ###################### The solve function computes all optimal solving maneuvers #####################################
import face
import cubie
import coord
import enums as en
import moves as mv
import pruning as pr
import geodesic_pruning as gp
from defs import N_TWIST

solutions = []


def _accept_solution(sofar, stats):
    global solutions
    if len(solutions) == 0 or len(solutions[-1]) == len(sofar):
        solutions.append(sofar[:])
        if stats is not None:
            stats['solutions'] += 1


def _search_baseline(cornperm, corntwist, sofar, togo, stats):
    """The original exhaustive optimal-path search."""
    if stats is not None:
        stats['search_nodes'] += 1
    if togo == 0:
        _accept_solution(sofar, stats)
        return

    for m in en.Move:
        if len(sofar) > 0 and sofar[-1] // 3 == m // 3:
            if stats is not None:
                stats['same_face_prunes'] += 1
            continue

        if stats is not None:
            stats['coordinate_lookups'] += 1
        cornperm_new = mv.cornperm_move[9 * cornperm + m]
        corntwist_new = mv.corntwist_move[9 * corntwist + m]

        if pr.corner_depth[N_TWIST * cornperm_new + corntwist_new] >= togo:
            if stats is not None:
                stats['distance_prunes'] += 1
            continue

        sofar.append(m)
        _search_baseline(
            cornperm_new, corntwist_new, sofar, togo - 1, stats)
        sofar.pop(-1)


def _search_pruned(
        cornperm,
        corntwist,
        sofar,
        togo,
        context,
        context_length,
        stats):
    """Search the certified language using precompiled continuation tuples."""
    if stats is not None:
        stats['search_nodes'] += 1
    if togo == 0:
        _accept_solution(sofar, stats)
        return

    if not sofar:
        moves = en.Move
    elif context_length < gp.MEMORY:
        moves = gp.REDUCED_NEXT_MOVES[context % gp.MOVE_COUNT]
        if stats is not None:
            stats['same_face_prunes'] += 3
    else:
        moves = gp.ALLOWED_NEXT_MOVES[context]
        if stats is not None:
            stats['same_face_prunes'] += 3
            stats['language_prunes'] += (
                len(gp.REDUCED_NEXT_MOVES[context % gp.MOVE_COUNT])
                - len(moves))

    for m in moves:
        if stats is not None:
            stats['coordinate_lookups'] += 1
        cornperm_new = mv.cornperm_move[9 * cornperm + m]
        corntwist_new = mv.corntwist_move[9 * corntwist + m]

        if pr.corner_depth[N_TWIST * cornperm_new + corntwist_new] >= togo:
            if stats is not None:
                stats['distance_prunes'] += 1
            continue

        sofar.append(m)
        if context_length < gp.MEMORY:
            context_new = context * gp.MOVE_COUNT + m
            context_length_new = context_length + 1
        else:
            context_new = gp.NEXT_CONTEXT[context][m]
            context_length_new = context_length
        _search_pruned(
            cornperm_new,
            corntwist_new,
            sofar,
            togo - 1,
            context_new,
            context_length_new,
            stats)
        sofar.pop(-1)


def search(
        cornperm,
        corntwist,
        sofar,
        togo,
        use_geodesic_pruning=False,
        stats=None):
    """Enumerate all optimal paths, or the certified complete subset."""
    if use_geodesic_pruning:
        _search_pruned(cornperm, corntwist, sofar, togo, 0, 0, stats)
    else:
        _search_baseline(cornperm, corntwist, sofar, togo, stats)


def solve(cubestring, use_geodesic_pruning=False):
    """Solves a 2x2x2 cube defined by its cube definition string.
     :param cubestring: The format of the string is given in the Facelet class defined in the file enums.py
     :param use_geodesic_pruning: If False, return every optimal maneuver as
       before. If True, return a certified nonempty subset of optimal
       maneuvers using the finite-memory geodesic language.
     :return A string containing optimal solving maneuvers
    """
    global solutions
    fc = face.FaceCube()
    s = fc.from_string(cubestring) #####################################################################################
    if s is not True:
        return s  # Error in facelet cube
    cc = fc.to_cubie_cube()
    s = cc.verify()
    if s != cubie.CUBE_OK:
        return s  # Error in cubie cube

    solutions = []
    co_cube = coord.CoordCube(cc)

    togo = pr.corner_depth[N_TWIST * co_cube.cornperm + co_cube.corntwist]
    search(
        co_cube.cornperm,
        co_cube.corntwist,
        [],
        togo,
        use_geodesic_pruning)

    s = ''
    for i in range(len(solutions)):  # use  range(min(len(solutions), 1)) if you want to return only a single solution
        ps = ''
        for m in solutions[i]:
            ps += m.name + ' '
        ps += '(' + str(len(ps)//3) + 'f)\r\n'
        s += ps
    return s
########################################################################################################################

