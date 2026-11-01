"""What the AI is rewarded for: the round result, plus small helpers that make the first steps learnable."""
from rl.observation import route, shot_path
from tank_game.config import SHOOT_COOLDOWN

SHAPING = 0.5           # total reward for walking the whole route to the enemy (0 = off)
AIM_BONUS = 0.3         # firing a shot that will hit the enemy, once per round so it can't be farmed
SELF_AIM_PENALTY = 0.3  # firing a shot that will come back and hit me, every time
FAST_WIN_BONUS = 1.0    # extra for winning, shrinking to 0 at the time limit: a win is worth 2 -> 1


def reward(game, i):
    """Only the round result for tank i: win +1, lose -1 (self-kill too), both dead -0.5."""
    if not game.done:
        return 0.0
    if game.winner == i:
        return 1.0
    if game.winner is None:  # the round only ends with no winner when both tanks died
        return -0.5
    return -1.0


class RoundReward:
    """Tank i's full reward during one round. Make a new one after every game.reset()."""

    def __init__(self, game, i, time_limit):
        self.game, self.i, self.time_limit = game, i, time_limit
        self.path0 = self.path = route(game, i)[1]
        self.aimed = False  # AIM_BONUS already given this round

    def tick(self):
        """Call after every game tick. A shot is judged when it's fired, not seconds later when it lands."""
        me = self.game.tanks[self.i]
        if not (me.alive and me.cooldown == SHOOT_COOLDOWN):  # on_shoot() just reset it: it fired this tick
            return 0.0
        hit = shot_path(self.game, self.i)[1]
        if hit and hit[0] == 1 - self.i and not self.aimed:
            self.aimed = True
            return AIM_BONUS
        if hit and hit[0] == self.i:
            return -SELF_AIM_PENALTY
        return 0.0

    def step(self):
        """Call after every decision: the result, the fast-win bonus and the progress along the route."""
        game = self.game
        r = reward(game, self.i)
        if game.done and game.winner == self.i:
            # Not a cost per second: that would make an early self-kill cheaper than waiting
            r += FAST_WIN_BONUS * max(0.0, 1 - game.time / self.time_limit)
        if all(t.alive for t in game.tanks):
            # Reward getting closer along the route, not being close: over a round it adds up to at most SHAPING
            path = route(game, self.i)[1]
            r += SHAPING * (self.path - path) / self.path0
            self.path = path
        return r
