# Tank AI

A 2D tank duel in a random maze, built as an environment for training an AI with **Reinforcement Learning (RL)**.

The goal: an agent that learns to play perfectly **only from experience**. It gets no hand-written strategy, no pathfinding and no aiming formulas. It just plays thousands of games and learns from the reward.

## The game

- Two square tanks in a randomly generated maze (a new map every round).
- Actions: **forward, backward, turn left, turn right, shoot**.
- Bullets bounce off walls and last 5 s. Each tank can have up to 5 bullets at once.
- One hit kills, **including your own bullets**.
- After the first death there is a short delay before the point is given. If both tanks die, nobody scores.

## Why it's a good RL problem

- **Bounces** make aiming non-trivial: the best shot is often off a wall, not straight at the enemy.
- **Self-kills** punish random shooting, so the agent has to learn when *not* to shoot.
- **Random mazes** stop the agent from memorizing one map, so it has to learn general skills.
- **Two players** allow **self-play**: the agent trains against copies of itself and keeps getting stronger.

## RL plan

1. **Environment**: wrap `Game` in a [Gymnasium](https://gymnasium.farama.org/) env (`reset()` / `step()`). The game logic has no drawing code, so it can run headless and much faster than real time.
2. **Observations**: what the agent "sees", for example:
   - its own position, angle and cooldown
   - raycasts in several directions (distance to walls)
   - the enemy's relative position and angle
   - nearby bullets (relative position and velocity)
3. **Actions**: the 5 buttons, as `MultiBinary(5)` or a small discrete set of combinations.
4. **Reward**:
   - `+1` for killing the enemy, `-1` for dying (worse if it was your own bullet)
   - small shaping rewards at first if learning is too slow (e.g. getting closer or having line of sight), removed later
5. **Algorithm**: PPO (e.g. Stable-Baselines3) as a first baseline.
6. **Training**: start against a random or static opponent, then move to **self-play** against older versions of itself.
7. **Evaluation**: win rate against fixed opponents and older versions, and watching games with the renderer.

## Run the game

```bash
uv pip install pygame-ce
python main.py
```

| Player | Move | Turn | Shoot |
|---|---|---|---|
| Red  | W / S | A / D | Space |
| Blue | ↑ / ↓ | ← / → | Enter |

`R` restarts the round, `Esc` quits.
