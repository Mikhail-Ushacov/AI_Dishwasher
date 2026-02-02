import gymnasium as gym
from gymnasium import spaces
import networkx as nx
import numpy as np
import os
from stable_baselines3 import PPO

class AdvancedKitchenEnv(gym.Env):
    def __init__(self):
        super().__init__()

        # --- ЛОКАЦИИ (УЗЛЫ) ---
        self.ZAKAZ = 0      # Где берем чек
        self.MESHOK = 1     # Картошка тут
        self.RAKOVINA = 2   # Мытье
        self.STOL = 3       # Резка
        self.PLITA = 4      # Жарка
        self.STOLIK = 5     # Клиент (финиш)

        # --- СОЗДАНИЕ ГРАФА ---
        self.graph = nx.Graph()
        # Соединяем точки (строим маршруты)
        self.graph.add_edge(self.ZAKAZ, self.MESHOK, weight=2)
        self.graph.add_edge(self.MESHOK, self.RAKOVINA, weight=2)
        self.graph.add_edge(self.RAKOVINA, self.STOL, weight=2)
        self.graph.add_edge(self.STOL, self.PLITA, weight=2)
        self.graph.add_edge(self.PLITA, self.STOLIK, weight=2)
        self.graph.add_edge(self.ZAKAZ, self.STOLIK, weight=5) # Доп. путь

        self.num_nodes = 6
        self.max_recipe_steps = 6 # 0:ничего, 1:заказ, 2:картошка, 3:мытая, 4:резаная, 5:жареная, 6:отдано

        # Наблюдение: [позиция, текущий_этап, предмет_в_руках]
        self.observation_space = spaces.MultiDiscrete([
            self.num_nodes,          # 0-5
            self.max_recipe_steps + 1, # 0-6
            2                        # 0 или 1
        ])

        # Действия: 0-5 (движение к узлу), 6 (взаимодействие: взять/помыть/готовить)
        self.action_space = spaces.Discrete(7)
        self.ACTION_INTERACT = 6

        self.max_steps = 100
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_node = self.ZAKAZ
        self.recipe_step = 0
        self.has_item = 0
        self.current_step = 0
        return self._get_obs(), {}

    def _get_obs(self):
        return np.array([self.current_node, self.recipe_step, self.has_item], dtype=np.int32)

    def step(self, action):
        action = int(np.asarray(action).item())
        self.current_step += 1
        reward = -0.1
        terminated = False
        truncated = False

        # --- ДВИЖЕНИЕ ---
        if action < self.num_nodes:
            if action == self.current_node:
                reward -= 0.1
            elif self.graph.has_edge(self.current_node, action):
                reward -= self.graph[self.current_node][action]["weight"]
                self.current_node = action
            else:
                reward -= 5 # Попытка пройти сквозь стену

        # --- ВЗАИМОДЕЙСТВИЕ (ACTION 6) ---
        elif action == self.ACTION_INTERACT:
            # 1. Взять заказ
            if self.recipe_step == 0 and self.current_node == self.ZAKAZ:
                self.recipe_step = 1
                reward += 10
            # 2. Взять картошку (нужен заказ)
            elif self.recipe_step == 1 and self.current_node == self.MESHOK:
                self.recipe_step = 2
                self.has_item = 1
                reward += 10
            # 3. Помыть картошку
            elif self.recipe_step == 2 and self.current_node == self.RAKOVINA:
                self.recipe_step = 3
                reward += 10
            # 4. Порезать картошку
            elif self.recipe_step == 3 and self.current_node == self.STOL:
                self.recipe_step = 4
                reward += 10
            # 5. Пожарить
            elif self.recipe_step == 4 and self.current_node == self.PLITA:
                self.recipe_step = 5
                reward += 10
            # 6. Отдать заказ
            elif self.recipe_step == 5 and self.current_node == self.STOLIK:
                self.recipe_step = 6
                reward += 50
                terminated = True
            else:
                reward -= 2 # Ошибка взаимодействия (не то место или время)

        if self.current_step >= self.max_steps:
            truncated = True

        return self._get_obs(), reward, terminated, truncated, {}

    def render(self):
        locs = ["Заказ", "Мешок", "Раковина", "Стол", "Плита", "Столик"]
        steps = ["Нет", "Заказ взят", "Есть картошка", "Помыта", "Порезана", "Пожарена", "Готово"]
        print(f"Шаг: {self.current_step} | Лок: {locs[self.current_node]} | Сост: {steps[self.recipe_step]}")

# ===============================
# ЗАПУСК И ОБУЧЕНИЕ
# ===============================
MODEL_PATH = "potato_pro_model"

if __name__ == "__main__":
    env = AdvancedKitchenEnv()

    if os.path.exists(MODEL_PATH + ".zip"):
        print("Загрузка обученного повара...")
        model = PPO.load(MODEL_PATH, env=env)
    else:
        # Увеличим ent_coef, так как цепочка длинная и нужно больше исследований
        model = PPO("MlpPolicy", env, verbose=1, learning_rate=1e-3, ent_coef=0.02)

    print("Обучение (это может занять больше времени из-за сложности)...")
    model.learn(total_timesteps=50000) # Длинная цепочка требует больше шагов
    model.save(MODEL_PATH)

    print("\n--- Тест алгоритма заказа ---")
    obs, _ = env.reset()
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, term, trunc, _ = env.step(action)
        env.render()
        done = term or trunc