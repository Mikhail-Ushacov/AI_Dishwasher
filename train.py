import os
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.monitor import Monitor
from kitchen_env import KitchenGraphEnv

def make_env():
    env = KitchenGraphEnv()
    env = Monitor(env)
    return env

def train():
    env = DummyVecEnv([make_env for _ in range(4)])
    
    env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.)

    model = PPO(
        "MlpPolicy", 
        env, 
        verbose=1,
        learning_rate=0.0003,
        n_steps=2048,
        batch_size=64,
        ent_coef=0.01,
        gamma=0.99
    )

    print("Starting training...")
    model.learn(total_timesteps=200_000)
    
    model.save("ppo_kitchen_chef")
    env.save("vec_normalize.pkl")
    print("Model saved.")
    return model, env

def evaluate_and_export():
    print("Running Eval...")
    env = DummyVecEnv([make_env])
    env = VecNormalize.load("vec_normalize.pkl", env)
    env.training = False
    
    model = PPO.load("ppo_kitchen_chef")
    
    obs = env.reset()
    done = False
    total_reward = 0
    
    raw_env = env.envs[0].unwrapped 
    
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, _ = env.step(action)
        total_reward += reward

    print(f"Eval Reward: {total_reward}")
    
    with open("simulation_replay.json", "w") as f:
        f.write(raw_env.get_json_history())
    print("Replay saved.")

if __name__ == "__main__":
    train()
    evaluate_and_export()