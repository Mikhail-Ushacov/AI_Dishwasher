import gymnasium as gym
from gymnasium import spaces
import networkx as nx
import numpy as np

from stable_baselines3 import PPO


class KitchenEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self):
        super().__init__()

        # ====== КУХНЯ (ГРАФ) ======
        # 0 - стол, 1 - плита, 2 - мойка
        self.graph = nx.Graph()
        self.graph.add_edge(0, 1, weight=2)
        self.graph.add_edge(1, 2, weight=3)
        self.graph.add_edge(0, 2, weight=4)

        self.STOL = 0
        self.PLITA = 1
        self.MOYKA = 2

        self.num_nodes = self.graph.number_of_nodes()

        # ====== РЕЦЕПТ ======
        # порядок действий обязателен
        self.recipe = ["take", "cook", "wash"]

        # ====== OBSERVATION ======
        # [позиция, шаг рецепта, есть_предмет]
        self.observation_space = spaces.MultiDiscrete([
            self.num_nodes,
            len(self.recipe),
            2
        ])

        # ====== ACTIONS ======
        # 0..2 -> move
        # 3 -> take
        # 4 -> cook
        # 5 -> wash
        self.ACTION_TAKE = self.num_nodes
        self.ACTION_COOK = self.num_nodes + 1
        self.ACTION_WASH = self.num_nodes + 2

        self.action_space = spaces.Discrete(self.num_nodes + 3)

        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.current_node = self.STOL
        self.recipe_step = 0
        self.has_item = 0

        return self._get_obs(), {}

    def step(self, action):
        action = int(action) 

        reward = 0
        terminated = False

        # ====== MOVE ======
        if action < self.num_nodes:
            if self.graph.has_edge(self.current_node, action):
                time_cost = self.graph[self.current_node][action]["weight"]
                self.current_node = action
                reward -= time_cost
            else:
                reward -= 5

        # ====== TAKE ======
        elif action == self.ACTION_TAKE:
            if (
                self.recipe[self.recipe_step] == "take"
                and self.current_node == self.STOL
                and self.has_item == 0
            ):
                self.has_item = 1
                self.recipe_step += 1
                reward += 10
            else:
                reward -= 2

        # ====== COOK ======
        elif action == self.ACTION_COOK:
            if (
                self.recipe[self.recipe_step] == "cook"
                and self.current_node == self.PLITA
                and self.has_item == 1
            ):
                self.recipe_step += 1
                reward += 10
            else:
                reward -= 2

        # ====== WASH ======
        elif action == self.ACTION_WASH:
            if (
                self.recipe[self.recipe_step] == "wash"
                and self.current_node == self.MOYKA
                and self.has_item == 1
            ):
                self.recipe_step += 1
                reward += 10
                reward += 20
                terminated = True
            else:
                reward -= 2

        return self._get_obs(), reward, terminated, False, {}

    def _get_obs(self):
        return np.array(
            [self.current_node, self.recipe_step, self.has_item],
            dtype=np.int32
        )


# ==============================
# ТЕСТ + ОБУЧЕНИЕ
# ==============================
if __name__ == "__main__":
    env = KitchenEnv()

    print("=== Random policy test ===")
    obs, _ = env.reset()
    done = False
    while not done:
        action = env.action_space.sample()
        obs, reward, done, _, _ = env.step(action)
        print(f"action={action}, obs={obs}, reward={reward}")

    print("\n=== Training PPO ===")
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        gamma=0.99
    )

    model.learn(total_timesteps=20_000)

    print("\n=== Trained agent ===")
    obs, _ = env.reset()
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, _, _ = env.step(action)
        print(f"action={action}, obs={obs}, reward={reward}")
