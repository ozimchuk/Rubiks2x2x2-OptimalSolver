import unittest

import geodesic_pruning as gp


OPTIMIZED_WORDS_BY_DEPTH = (
    1,
    9,
    54,
    324,
    1908,
    11286,
    66744,
    394734,
    2334510,
    13806612,
    81654186,
    482913990,
)


def decode(code, length=4):
    moves = [0] * length
    for index in range(length - 1, -1, -1):
        code, moves[index] = divmod(code, 9)
    return moves


class GeodesicPruningTest(unittest.TestCase):
    def test_certificate_dimensions(self):
        self.assertEqual(36, len(gp.FORBIDDEN_MOTIFS))
        self.assertEqual(47, gp.DFA_STATE_COUNT)
        self.assertNotEqual(gp.START_STATE, gp.DEAD_STATE)

    def test_every_forbidden_motif_reaches_dead(self):
        for code in gp.FORBIDDEN_MOTIFS:
            state = gp.START_STATE
            moves = decode(code)
            for move in moves[:-1]:
                state = gp.transition(state, move)
                self.assertNotEqual(gp.DEAD_STATE, state)
            self.assertEqual(
                gp.DEAD_STATE,
                gp.transition(state, moves[-1]),
                code)

    def test_exact_language_counts(self):
        counts = [0] * gp.DFA_STATE_COUNT
        counts[gp.START_STATE] = 1
        by_depth = [1]
        for _ in range(11):
            next_counts = [0] * gp.DFA_STATE_COUNT
            for state, count in enumerate(counts):
                if state == gp.DEAD_STATE or count == 0:
                    continue
                for move in range(9):
                    target = gp.transition(state, move)
                    if target != gp.DEAD_STATE:
                        next_counts[target] += count
            counts = next_counts
            by_depth.append(sum(counts))
        self.assertEqual(OPTIMIZED_WORDS_BY_DEPTH, tuple(by_depth))

    def test_hot_path_tables_match_dfa(self):
        for code in range(9 ** gp.MEMORY):
            prefix = decode(code, gp.MEMORY)
            if any(
                    prefix[index] // 3 == prefix[index + 1] // 3
                    for index in range(gp.MEMORY - 1)):
                continue
            state = gp.START_STATE
            for move in prefix:
                state = gp.transition(state, move)
            for move in range(9):
                dfa_accepts = (
                    gp.transition(state, move) != gp.DEAD_STATE)
                hot_path_accepts = move in gp.ALLOWED_NEXT_MOVES[code]
                self.assertEqual(
                    dfa_accepts, hot_path_accepts, (code, move))


if __name__ == '__main__':
    unittest.main()
