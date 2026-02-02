import gymnasium as gym
from gymnasium import spaces
import networkx as nx
import numpy as np
import os
from stable_baselines3 import PPO

class KitchenEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self):
        super().__init__()
        # Узлы
        self.STOL, self.PLITA, self.MOYKA = 0, 1, 2

        self.graph = nx.Graph()
        self.graph.add_edge(self.STOL, self.PLITA, weight=2)
        self.graph.add_edge(self.PLITA, self.MOYKA, weight=3)
        self.graph.add_edge(self.STOL, self.MOYKA, weight=4)

        self.num_nodes = self.graph.number_of_nodes()
        self.max_recipe_steps = 3 

        self.observation_space = spaces.MultiDiscrete([
            self.num_nodes,
            self.max_recipe_steps + 1, 
            2
        ])

        self.ACTION_TAKE, self.ACTION_COOK, self.ACTION_WASH = 3, 4, 5
        self.action_space = spaces.Discrete(6)

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
        # Исправление ошибки unhashable type (numpy to int)
        action = int(np.asarray(action).item())
        
        self.current_step += 1
        reward = -0.1
        terminated = False
        truncated = False

        # Движение
        if action < self.num_nodes:
            if action == self.current_node:
                reward -= 0.1
            elif self.graph.has_edge(self.current_node, action):
                reward -= self.graph[self.current_node][action]["weight"]
                self.current_node = action
            else:
                reward -= 2

        # Действия
        elif action == self.ACTION_TAKE:
            if self.recipe_step == 0 and self.current_node == self.STOL:
                self.has_item, self.recipe_step, reward = 1, 1, 15
            else: reward -= 1

        elif action == self.ACTION_COOK:
            if self.recipe_step == 1 and self.current_node == self.PLITA and self.has_item == 1:
                self.recipe_step, reward = 2, 15
            else: reward -= 1

        elif action == self.ACTION_WASH:
            if self.recipe_step == 2 and self.current_node == self.MOYKA and self.has_item == 1:
                self.recipe_step, reward, terminated = 3, 50, True
            else: reward -= 1

        if self.current_step >= self.max_steps:
            truncated = True

        return self._get_obs(), reward, terminated, truncated, {}

    def _get_obs(self):
        return np.array([self.current_node, self.recipe_step, self.has_item], dtype=np.int32)

    def render(self):
        locs = {0: "Стол", 1: "Плита", 2: "Мойка"}
        print(f"Шаг: {self.current_step} | {locs[self.current_node]} | Рецепт: {self.recipe_step} | Предмет: {self.has_item}")

# ===============================
# ЛОГИКА ОБУЧЕНИЯ И ПАМЯТИ
# ===============================
MODEL_PATH = "kitchen_model"

if __name__ == "__main__":
    env = KitchenEnv()

    # Проверяем, есть ли уже сохраненный агент
    if os.path.exists(MODEL_PATH + ".zip"):
        print(f"--- Найдена сохраненная модель '{MODEL_PATH}'. Загружаем и продолжаем обучение... ---")
        model = PPO.load(MODEL_PATH, env=env)
    else:
        print("--- Сохраненной модели нет. Начинаем обучение с нуля... ---")
        model = PPO("MlpPolicy", env, verbose=1, learning_rate=1e-3)

    # Обучаем (можно запускать этот скрипт много раз, он будет развиваться)
    print("Обучение...")
    model.learn(total_timesteps=10000)
    
    # СОХРАНЯЕМ прогресс
    model.save(MODEL_PATH)
    print(f"--- Модель сохранена в '{MODEL_PATH}.zip' ---")

    # Демонстрация
    print("\n--- Тест текущего навыка агента ---")
    obs, _ = env.reset()
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, term, trunc, _ = env.step(action)
        env.render()
        done = term or trunc