import gymnasium as gym
from gymnasium import spaces
import numpy as np
import json
import config
from world import KitchenWorld

class KitchenGraphEnv(gym.Env):
    metadata = {"render_modes": ["human", "json"]}

    def __init__(self):
        super().__init__()
        self.world = KitchenWorld()
        self.num_nodes = len(config.NODE_CONFIG)

        # === ACTION SPACE ===
        # 0 to N-1: Move to specific Node
        # N: Interact (Context sensitive)
        self.act_move_limit = self.num_nodes
        self.ACT_INTERACT = self.num_nodes
        self.action_space = spaces.Discrete(self.num_nodes + 1)

        # === OBSERVATION SPACE ===
        # 1. Agent: Node (1), Inventory Slots (MAX_INV)
        # 2. Distances: From current node to all other nodes (Num_Nodes) - Helps navigation
        # 3. Stations: [HasItem, ItemType, IsBusy, TimerNorm] * Num_Nodes
        # 4. Orders: [ItemType, TimeNorm] * MAX_ORDERS
        
        agent_dim = 1 + config.MAX_INVENTORY
        dist_dim = self.num_nodes
        station_dim = self.num_nodes * 4
        order_dim = config.MAX_ORDERS * 2
        
        total_obs = agent_dim + dist_dim + station_dim + order_dim
        
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(total_obs,), dtype=np.float32
        )

        self.history = []

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.world.reset()
        self.history = []
        return self._get_obs(), {}

    def step(self, action):
        action = int(action)
        reward = 0
        time_passed = 0
        
        if action < self.act_move_limit:
            target = action
            if target == self.world.agent_node:
                time_passed = 1
                reward += -0.1
            else:
                time_passed = self.world.move_agent(target)
                
        elif action == self.ACT_INTERACT:
            time_passed = 1
            r_int = self._handle_interaction()
            reward += r_int

        expired_orders = self.world.tick_time(time_passed)
        
        reward += (time_passed * config.TIME_STEP_PENALTY)
        reward += (expired_orders * config.FAILURE_PENALTY)
        
        terminated = False
        truncated = self.world.global_time >= config.MAX_STEPS

        self.history.append(self.world.get_snapshot())

        return self._get_obs(), reward, terminated, truncated, {}

    def _handle_interaction(self):
        """Complex logic for Pick/Place/Process."""
        w = self.world
        agent_node = w.agent_node
        station = w.stations[agent_node]
        reward = 0

        # --- CASE 1: DELIVERY STATION ---
        if station.type == config.ST_DELIVERY:
            delivered_something = False
            # Check inventory for matching orders
            items_to_keep = []
            for item in w.inventory:
                # Find matching order
                match = next((o for o in w.orders if o.item_type == item.type_id), None)
                if match:
                    # Success!
                    reward += config.SUCCESS_REWARD
                    # Bonus for speed
                    reward += (match.time_remaining / config.ORDER_TTL) * 2.0
                    w.orders.remove(match)
                    delivered_something = True
                else:
                    items_to_keep.append(item)
            w.inventory = items_to_keep
            return reward if delivered_something else config.INVALID_ACTION_PENALTY

        # --- CASE 2: SOURCE STATION ---
        if station.type == config.ST_SOURCE:
            if len(w.inventory) < config.MAX_INVENTORY:
                # Pick up ingredient
                new_item = w.create_item(station.source_item)
                w.inventory.append(new_item)
                return 0.5 # Small reward for picking up needed items
            return config.INVALID_ACTION_PENALTY # Full inventory

        # --- CASE 3: PROCESS STATION ---
        if station.type == config.ST_PROCESS:
            
            # Sub-case: Station has finished item -> Pickup
            if station.held_item and not station.is_busy:
                if len(w.inventory) < config.MAX_INVENTORY:
                    w.inventory.append(station.held_item)
                    station.held_item = None
                    return 1.0 # Good job picking up finished goods
                return config.INVALID_ACTION_PENALTY # Full inv

            # Sub-case: Station is empty -> Place item to cook
            if not station.held_item:
                # Look for valid item in inventory
                for idx, item in enumerate(w.inventory):
                    recipe_key = (item.type_id, station.name)
                    if recipe_key in config.RECIPES:
                        # Found valid recipe!
                        rec = config.RECIPES[recipe_key]
                        
                        # Transform item
                        item.type_id = rec["out"]
                        w.inventory.pop(idx)
                        
                        # Place on station and start
                        station.held_item = item
                        station.start_processing(rec["time"])
                        
                        return config.SUBGOAL_REWARD # Big hint: "You started cooking!"
                
                return config.INVALID_ACTION_PENALTY # No valid item to cook

            # Sub-case: Station is busy
            return config.INVALID_ACTION_PENALTY

        return 0

    def _get_obs(self):
        """Flatten state into normalized vector."""
        w = self.world
        obs = []

        # 1. Agent Node (Normalized 0-1)
        obs.append(w.agent_node / self.num_nodes)
        
        # 2. Inventory (Pad with 0)
        inv_ids = [i.type_id for i in w.inventory]
        inv_ids += [0] * (config.MAX_INVENTORY - len(inv_ids))
        # Normalize item IDs loosely (assuming max ID is < 10)
        obs.extend([i / 10.0 for i in inv_ids])

        # 3. Distances from current node (Crucial for nav)
        dists = w.distances[w.agent_node]
        for i in range(self.num_nodes):
            d = dists.get(i, 10)
            obs.append(min(d, 20.0) / 20.0) # Normalize cap at 20s

        # 4. Stations
        for i in range(self.num_nodes):
            st = w.stations[i]
            obs.append(1.0 if st.held_item else 0.0) # Has Item
            obs.append((st.held_item.type_id if st.held_item else 0) / 10.0) # Item Type
            obs.append(1.0 if st.is_busy else 0.0) # Busy
            obs.append(st.timer / 20.0) # Timer (approx norm)

        # 5. Orders
        for i in range(config.MAX_ORDERS):
            if i < len(w.orders):
                o = w.orders[i]
                obs.append(o.item_type / 10.0)
                obs.append(o.time_remaining / config.ORDER_TTL)
            else:
                obs.extend([0.0, 0.0])

        return np.array(obs, dtype=np.float32)

    def get_json_history(self):
        return json.dumps(self.history, indent=2)