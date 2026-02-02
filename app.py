import gymnasium as gym
from gymnasium import spaces
import numpy as np
from .moduls.kitchen_map import KitchenMap, KITCHEN_MATRIX


class KitchenEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self):
        super().__init__()

        self.map = KitchenMap(KITCHEN_MATRIX)
        self.graph = self.map.graph

        self.STOL = self.map.STOL
        self.PLITA = self.map.PLITA
        self.MOYKA = self.map.MOYKA

        self.num_nodes = self.graph.number_of_nodes()
        self.max_recipe_steps = 3

        self.observation_space = spaces.MultiDiscrete([
            self.num_nodes,
            self.max_recipe_steps + 1,
            2
        ])

        self.ACTION_TAKE = self.num_nodes
        self.ACTION_COOK = self.num_nodes + 1
        self.ACTION_WASH = self.num_nodes + 2
        self.action_space = spaces.Discrete(self.num_nodes + 3)

        self.max_steps = 50
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_node = self.STOL
        self.recipe_step = 0
        self.has_item = 0
        self.current_step = 0
        return self._get_obs(), {}

    def step(self, action):
        action = int(action)
        self.current_step += 1

        reward = -0.1
        terminated = False
        truncated = False

        # Перемещение
        if action < self.num_nodes:
            if action == self.current_node:
                reward -= 0.1
            elif self.graph.has_edge(self.current_node, action):
                cost = self.graph[self.current_node][action]["weight"]
                reward -= cost
                self.current_node = action
            else:
                reward -= 2

        # Взять
        elif action == self.ACTION_TAKE:
            if self.recipe_step == 0 and self.current_node == self.STOL:
                self.has_item = 1
                self.recipe_step = 1
                reward = 15
            else:
                reward -= 1

        # Готовить
        elif action == self.ACTION_COOK:
            if self.recipe_step == 1 and self.current_node == self.PLITA:
                self.recipe_step = 2
                reward = 15
            else:
                reward -= 1

        # Мыть
        elif action == self.ACTION_WASH:
            if self.recipe_step == 2 and self.current_node == self.MOYKA:
                self.recipe_step = 3
                reward = 50
                terminated = True
            else:
                reward -= 1

        if self.current_step >= self.max_steps:
            truncated = True

        return self._get_obs(), reward, terminated, truncated, {}

    def _get_obs(self):
        return np.array(
            [self.current_node, self.recipe_step, self.has_item],
            dtype=np.int32
        )

    def render(self):
        names = {0: "Стол", 1: "Плита", 2: "Мойка"}
        print(
            f"Шаг {self.current_step} | "
            f"{names[self.current_node]} | "
            f"Рецепт {self.recipe_step} | "
            f"Предмет {self.has_item}"
        )
