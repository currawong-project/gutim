from typing import List, Tuple


def smith_waterman(
    seq1: List[int],
    seq2: List[int],
    match_score: int = 2,
    mismatch_score: int = -1,
    gap_penalty: int = -1,
) -> Tuple[int, List[int], List[int]]:
    """
    Perform Smith-Waterman local alignment on two integer sequences.

    Returns:
        (best_score, aligned_seq1, aligned_seq2)

    Gaps are represented by None.
    """

    rows = len(seq1) + 1
    cols = len(seq2) + 1

    # Dynamic programming score matrix
    H = [[0] * cols for _ in range(rows)]

    # Traceback directions
    STOP = 0
    DIAG = 1
    UP = 2
    LEFT = 3

    traceback = [[STOP] * cols for _ in range(rows)]

    best_score = 0
    best_i = 0
    best_j = 0

    # Fill DP table
    for i in range(1, rows):
        for j in range(1, cols):

            score = match_score if seq1[i - 1] == seq2[j - 1] else mismatch_score

            diag = H[i - 1][j - 1] + score
            up = H[i - 1][j] + gap_penalty
            left = H[i][j - 1] + gap_penalty

            best = max(0, diag, up, left)
            H[i][j] = best

            if best == 0:
                traceback[i][j] = STOP
            elif best == diag:
                traceback[i][j] = DIAG
            elif best == up:
                traceback[i][j] = UP
            else:
                traceback[i][j] = LEFT

            if best > best_score:
                best_score = best
                best_i = i
                best_j = j

    # Trace back from highest-scoring cell
    #
    # mapping[i] gives the index in seq2 aligned with seq1[i],
    # or None if seq1[i] is not aligned.
    mapping = [None] * len(seq1)

    i = best_i
    j = best_j

    while traceback[i][j] != STOP:

        if traceback[i][j] == DIAG:
            # seq1[i-1] aligns with seq2[j-1]
            mapping[i - 1] = j - 1
            i -= 1
            j -= 1

        elif traceback[i][j] == UP:
            # seq1[i-1] aligns to a gap
            mapping[i - 1] = None
            i -= 1

        elif traceback[i][j] == LEFT:
            # gap in seq1; no mapping to record
            j -= 1

    return best_score, mapping

if __name__ == "__main__":

    x0 = [10,20,30]
    x1 = [0,10,0,20,30]
    match_score = 2
    mismatch_penalty = -1
    gap_penalty = -1
    print(smith_waterman(x0,x1,match_score,mismatch_penalty,gap_penalty))
    
