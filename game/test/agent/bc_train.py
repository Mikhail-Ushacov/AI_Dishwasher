import os
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.vec_env import DummyVecEnv

from agent.env import KitchenEnv
from agent.config import TrainingConfig
from agent.scripted import ScriptedAgent
from agent.models.cnn import KitchenCNN


def collect_demos(config, n_episodes=50, max_steps=500) -> tuple:
    import copy as _copy
    obs_list = []
    act_list = []
    scripted = ScriptedAgent()

    from agent.reward import RewardConfig
    demo_reward = RewardConfig.dense()
    demo_reward.goal_shaping = 0.0  # no shaping for demos

    for ep in range(n_episodes):
        env = KitchenEnv(
            map_name=config.map_name,
            max_steps=config.max_steps_per_episode,
            reward_config=demo_reward,
            seed=config.seed + ep,
        )

        obs, _ = env.reset()
        done = False
        step = 0

        while not done and step < max_steps:
            path = scripted.get_actions(env.player, env.kitchen, env.level)
            action = path[0] if path else 6
            obs_list.append(obs.copy())
            act_list.append(action)
            obs, _, term, trunc, _ = env.step(action)
            step += 1
            done = term or trunc

        env.close()

    return np.array(obs_list), np.array(act_list, dtype=np.int64)


def pretrain_with_bc(model, observations, actions, epochs=50, batch_size=256, lr=1e-3):
    counts = np.bincount(actions, minlength=7)

    # Class weights: inverse frequency, capped to avoid over-emphasis
    weights = np.ones(7, dtype=float)
    for a in range(7):
        if counts[a] > 0:
            weights[a] = counts.max() / counts[a]
    weights = weights.clip(0.1, 10.0)
    weights = weights / weights.sum() * 7
    class_weight = torch.from_numpy(weights).float().to(model.device)
    print(f"  Class weights: {weights.round(2).tolist()}")

    # Oversample rare actions to match majority class
    obs_aug, act_aug = [], []
    for a in range(7):
        mask = actions == a
        n_orig = mask.sum()
        if n_orig == 0:
            continue
        factor = int(counts.max()) // n_orig
        if factor > 1:
            obs_aug.append(np.tile(observations[mask], (factor, 1, 1, 1)))
            act_aug.append(np.tile(actions[mask], factor))
        else:
            obs_aug.append(observations[mask])
            act_aug.append(actions[mask])

    obs_all = np.concatenate(obs_aug) if len(obs_aug) > 1 else obs_aug[0]
    act_all = np.concatenate(act_aug) if len(act_aug) > 1 else act_aug[0]
    print(f"  Oversampled dataset: {len(obs_all)} transitions (from {len(observations)})")

    dataset = TensorDataset(
        torch.from_numpy(obs_all).float(),
        torch.from_numpy(act_all).long(),
    )
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    policy = model.policy
    policy.train()
    optimizer = torch.optim.Adam(policy.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss(weight=class_weight)

    for epoch in range(epochs):
        total_loss = 0.0
        n_batches = 0
        for obs_batch, act_batch in loader:
            obs_batch = obs_batch.to(model.device)
            act_batch = act_batch.to(model.device)

            with torch.no_grad():
                features = policy.extract_features(obs_batch)
            logits = policy.action_net(features)
            loss = loss_fn(logits, act_batch)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        if (epoch + 1) % 10 == 0:
            print(f"  BC epoch {epoch+1}/{epochs}: loss={total_loss/n_batches:.4f}")

    with torch.no_grad():
        all_obs_t = torch.from_numpy(observations).float().to(model.device)
        all_logits = policy.action_net(policy.extract_features(all_obs_t))
        preds = all_logits.argmax(dim=1).cpu().numpy()
        accuracy = (preds == actions).mean()
        per_class = np.array([(preds == a)[actions == a].mean() if (actions == a).sum() > 0 else 0.0 for a in range(7)])
    print(f"  BC overall accuracy: {accuracy*100:.1f}%")
    for i, label in enumerate(['UP','DOWN','LEFT','RIGHT','INTERACT','INTERACT_SEC','WAIT']):
        print(f"    {label:12s}: {per_class[i]*100:.1f}%")


def train_with_bc(config: TrainingConfig):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print("=" * 50)
    print("BC Pretraining Pipeline")
    print("=" * 50)
    print(f"  Map: {config.map_name}")
    print(f"  Device: {device}")
    print()

    os.makedirs(os.path.dirname(config.save_path), exist_ok=True)

    print("Step 1: Collecting demonstrations...")
    start = time.time()
    observations, actions = collect_demos(config, n_episodes=50)
    elapsed = time.time() - start
    print(f"  Collected {len(observations)} transitions in {elapsed:.0f}s")
    print(f"  Action distribution: {np.bincount(actions, minlength=7)}")

    print("\nStep 2: Creating env for feature dimensions...")
    env = DummyVecEnv([lambda: ActionMasker(
        KitchenEnv(map_name=config.map_name, max_steps=config.max_steps_per_episode,
                   reward_config=config.reward_config),
        lambda e: e.action_masks(),
    )])

    print("Step 3: Creating PPO model (random init)...")
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
        policy_kwargs={
            "features_extractor_class": KitchenCNN,
            "features_extractor_kwargs": {"features_dim": config.features_dim},
            "net_arch": [128, 64],
        },
        tensorboard_log=config.tensorboard_log,
        verbose=0,
        seed=config.seed,
        device=device,
    )

    print("\nStep 4: Pretraining with Behavioral Cloning...")
    pretrain_with_bc(model, observations, actions, epochs=50)

    print("\nStep 5: Fine-tuning with PPO...")
    model.learn(total_timesteps=config.total_timesteps, progress_bar=True)

    model.save(config.save_path)
    print(f"\nModel saved to {config.save_path}.zip")

    env.close()
    return model
