def reward(game, i):
    """Only the round result for tank i: win +1, lose -1 (self-kill too), both dead -0.5."""
    if not game.done:
        return 0.0
    if game.winner == i:
        return 1.0
    if game.winner is None:  # the round only ends with no winner when both tanks died
        return -0.5
    return -1.0
