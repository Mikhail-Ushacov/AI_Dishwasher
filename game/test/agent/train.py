import os
import time
import torch
from stable_baselines3.common.vec_env import DummyVecEnv
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

from agent.env import KitchenEnv
from agent.config import TrainingConfig
from agent.models.cnn import KitchenCNN


def _resolve_device(device: str) -> str:
    if device == "auto":
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    return device


def _print_resource_summary(config: TrainingConfig, device: str):
    print("=" * 50)
    print("Resource Summary")
    print("=" * 50)
    print(f"  Device:          {device}")
    print(f"  CPU cores:       {os.cpu_count()} logical / {os.cpu_count() // 2} physical")
    if device == "cuda":
        print(f"  GPU:             {torch.cuda.get_device_name(0)}")
        print(f"  VRAM:            {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    print(f"  Parallel envs:   {config.n_envs}")
    print(f"  n_steps:         {config.n_steps}")
    print(f"  batch_size:      {config.batch_size}")
    steps_per_update = config.n_envs * config.n_steps
    updates = config.total_timesteps // steps_per_update
    print(f"  Steps/update:    {steps_per_update}")
    print(f"  Total updates:   {updates}")
    print(f"  Total timesteps: {config.total_timesteps}")
    print("=" * 50)


def _make_env(config: TrainingConfig, rank: int):
    def _init():
        env = KitchenEnv(
            map_name=config.map_name,
            max_steps=config.max_steps_per_episode,
            reward_config=config.reward_config,
            seed=config.seed + rank if config.seed else None,
        )
        env = ActionMasker(env, lambda e: e.action_masks())
        return env
    return _init


def train(config: TrainingConfig):
    device = _resolve_device(config.device)

    if device == "cpu":
        torch.set_num_threads(min(4, os.cpu_count() or 4))

    _print_resource_summary(config, device)

    os.makedirs(os.path.dirname(config.save_path), exist_ok=True)
    if config.tensorboard_log:
        os.makedirs(config.tensorboard_log, exist_ok=True)

    env = DummyVecEnv([_make_env(config, i) for i in range(config.n_envs)])

    policy_kwargs = {
        "features_extractor_class": KitchenCNN,
        "features_extractor_kwargs": {"features_dim": config.features_dim},
        "net_arch": [128, 64],
    }

    start = time.time()

    model = MaskablePPO(
        "CnnPolicy",
        env,
        learning_rate=config.learning_rate,
        n_steps=config.n_steps,
        batch_size=config.batch_size,
        n_epochs=config.n_epochs,
        gamma=config.gamma,
        gae_lambda=config.gae_lambda,
        clip_range=config.clip_range,
        ent_coef=config.ent_coef,
        vf_coef=config.vf_coef,
        max_grad_norm=config.max_grad_norm,
        policy_kwargs=policy_kwargs,
        tensorboard_log=config.tensorboard_log,
        verbose=1,
        seed=config.seed,
        device=device,
    )

    model.learn(
        total_timesteps=config.total_timesteps,
        progress_bar=True,
    )

    elapsed = time.time() - start
    model.save(config.save_path)

    if config.tensorboard_log:
        model.logger.record("time/total_seconds", elapsed)

    steps_per_sec = config.total_timesteps / elapsed
    print(f"\nTraining finished in {elapsed:.1f}s ({steps_per_sec:.0f} steps/s)")
    print(f"Model saved to {config.save_path}.zip")

    env.close()
    return model


def train_entry():
    config = TrainingConfig()
    train(config)


if __name__ == "__main__":
    train_entry()
