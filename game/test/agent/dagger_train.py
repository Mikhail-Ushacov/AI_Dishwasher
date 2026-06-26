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
from agent.eval import Evaluator


def dagger_collect(model, env, scripted, n_episodes=20, beta=0.5):
    """Roll out episodes mixing expert (beta) and policy (1-beta) actions."""
    new_obs, new_acts = [], []
    for ep in range(n_episodes):
        obs, _ = env.reset()
        done = False
        step = 0
        while not done and step < 300:
            expert_path = scripted.get_actions(env.player, env.kitchen, env.level)
            expert_action = expert_path[0] if expert_path else 6

            masks = env.action_masks()
            if np.random.random() < beta:
                action = expert_action
            else:
                obs_t = torch.from_numpy(obs).float().unsqueeze(0).to(model.device)
                with torch.no_grad():
                    features = model.policy.extract_features(obs_t)
                    logits = model.policy.action_net(features)
                if masks is not None:
                    logits[:, ~np.array(masks)] = -1e8
                action = logits.argmax(dim=1).item()

            new_obs.append(obs.copy())
            new_acts.append(expert_action)
            obs, _, term, trunc, _ = env.step(action)
            step += 1
            done = term or trunc
    return np.array(new_obs), np.array(new_acts, dtype=np.int64)


def dagger_train(config: TrainingConfig, n_iters=5, n_episodes_per_iter=30, bc_epochs=30):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    scripted = ScriptedAgent()
    all_obs, all_acts = [], []

    for it in range(n_iters + 1):
        print(f"\n{'='*50}")
        print(f"DAgger Iteration {it+1}/{n_iters+1}")
        print(f"{'='*50}")

        # Create env for rollout (stateful for player/kitchen access)
        env = KitchenEnv(
            map_name=config.map_name,
            max_steps=config.max_steps_per_episode,
            seed=config.seed + it,
        )

        if it == 0:
            # Walkthrough: pure expert demonstration
            print("  Walking through with pure expert...")
            for ep in range(n_episodes_per_iter):
                obs, _ = env.reset()
                done = False
                step = 0
                while not done and step < 300:
                    path = scripted.get_actions(env.player, env.kitchen, env.level)
                    action = path[0] if path else 6
                    all_obs.append(obs.copy())
                    all_acts.append(action)
                    obs, _, term, trunc, _ = env.step(action)
                    step += 1
                    done = term or trunc
        else:
            # Collect from mixed policy (beta decreases over time)
            beta = max(0.1, 0.8 * (1 - (it - 1) / n_iters))
            n_rollout = n_episodes_per_iter // 2
            n_guided = n_episodes_per_iter - n_rollout

            print(f"  Beta={beta:.2f} ({n_rollout} rollout + {n_guided} guided = {n_episodes_per_iter})")

            # Pure policy rollout (no beta) to collect policy-visited states
            for ep in range(n_rollout):
                obs, _ = env.reset()
                done = False
                step = 0
                while not done and step < 300:
                    path = scripted.get_actions(env.player, env.kitchen, env.level)
                    expert_action = path[0] if path else 6
                    masks = env.action_masks()
                    obs_t = torch.from_numpy(obs).float().unsqueeze(0).to(model.device)
                    with torch.no_grad():
                        features = model.policy.extract_features(obs_t)
                        logits = model.policy.action_net(features)
                    if masks is not None:
                        logits[:, ~np.array(masks)] = -1e8
                    action = logits.argmax(dim=1).item()
                    all_obs.append(obs.copy())
                    all_acts.append(expert_action)  # expert corrects
                    obs, _, term, trunc, _ = env.step(action)
                    step += 1
                    done = term or trunc

            # Mixed rollout
            for ep in range(n_guided):
                obs, _ = env.reset()
                done = False
                step = 0
                while not done and step < 300:
                    path = scripted.get_actions(env.player, env.kitchen, env.level)
                    expert_action = path[0] if path else 6
                    masks = env.action_masks()
                    if np.random.random() < beta:
                        action = expert_action
                    else:
                        obs_t = torch.from_numpy(obs).float().unsqueeze(0).to(model.device)
                        with torch.no_grad():
                            features = model.policy.extract_features(obs_t)
                            logits = model.policy.action_net(features)
                        if masks is not None:
                            logits[:, ~np.array(masks)] = -1e8
                        action = logits.argmax(dim=1).item()
                    all_obs.append(obs.copy())
                    all_acts.append(expert_action)
                    obs, _, term, trunc, _ = env.step(action)
                    step += 1
                    done = term or trunc

        env.close()

        obs_np = np.array(all_obs)
        acts_np = np.array(all_acts, dtype=np.int64)
        print(f"  Aggregated dataset: {len(obs_np)} transitions")
        print(f"  Action distribution: {np.bincount(acts_np, minlength=7)}")

        # Train on aggregated data
        if it == 0:
            print("  Creating model...")
            env_vec = DummyVecEnv([lambda: ActionMasker(
                KitchenEnv(map_name=config.map_name, max_steps=config.max_steps_per_episode),
                lambda e: e.action_masks(),
            )])
            model = MaskablePPO(
                'CnnPolicy', env_vec,
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
                    'features_extractor_class': KitchenCNN,
                    'features_extractor_kwargs': {'features_dim': config.features_dim},
                    'net_arch': [128, 64],
                },
                tensorboard_log=config.tensorboard_log,
                verbose=0,
                seed=config.seed,
                device=device,
            )
        else:
            pass  # reuse existing model

        # Train BC on aggregated dataset
        counts = np.bincount(acts_np, minlength=7)
        weights = np.ones(7, dtype=float)
        for a in range(7):
            if counts[a] > 0:
                weights[a] = counts.max() / counts[a]
        weights = weights.clip(0.1, 10.0)
        weights = weights / weights.sum() * 7
        class_weight = torch.from_numpy(weights).float().to(device)
        print(f"  Class weights: {weights.round(2).tolist()}")

        obs_aug, act_aug = [], []
        for a in range(7):
            mask = acts_np == a
            n_orig = mask.sum()
            if n_orig == 0:
                continue
            factor = int(counts.max()) // n_orig
            if factor > 1:
                obs_aug.append(np.tile(obs_np[mask], (factor, 1, 1, 1)))
                act_aug.append(np.tile(acts_np[mask], factor))
            else:
                obs_aug.append(obs_np[mask])
                act_aug.append(acts_np[mask])

        obs_all = np.concatenate(obs_aug)
        act_all = np.concatenate(act_aug)
        print(f"  Oversampled: {len(obs_all)}")

        dataset = TensorDataset(
            torch.from_numpy(obs_all).float(),
            torch.from_numpy(act_all).long(),
        )
        loader = DataLoader(dataset, batch_size=256, shuffle=True)

        policy = model.policy
        policy.train()
        optimizer = torch.optim.Adam(policy.parameters(), lr=1e-3)
        loss_fn = nn.CrossEntropyLoss(weight=class_weight)

        for epoch in range(bc_epochs):
            total_loss = 0.0
            nb = 0
            for obs_batch, act_batch in loader:
                obs_batch = obs_batch.to(device)
                act_batch = act_batch.to(device)
                with torch.no_grad():
                    features = policy.extract_features(obs_batch)
                logits = policy.action_net(features)
                loss = loss_fn(logits, act_batch)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
                nb += 1
            if (epoch + 1) % 10 == 0:
                print(f"    epoch {epoch+1}/{bc_epochs}: loss={total_loss/nb:.4f}")

        # Evaluate
        print("  Evaluating...")
        records = Evaluator().evaluate(model, maps=[config.map_name], n_episodes=10, seed=config.seed + it * 100)
        print(f"  Reward: {np.mean([r.total_reward for r in records]):.2f}, "
              f"Orders: {sum(1 for r in records if r.orders_completed > 0)}/10, "
              f"Score: {np.mean([r.final_score for r in records]):.1f}")

        env_vec.close()

    return model


if __name__ == "__main__":
    config = TrainingConfig(
        map_name='map1.tmx',
        save_path='agent/models/ppo_map1_dagger',
        seed=42,
    )
    os.makedirs('agent/models', exist_ok=True)
    model = dagger_train(config, n_iters=5, n_episodes_per_iter=30, bc_epochs=50)
    model.save(config.save_path)
    print(f"\nSaved to {config.save_path}.zip")

    print("\nFinal evaluation (20 episodes)...")
    records = Evaluator().evaluate(model, maps=['map1.tmx'], n_episodes=20, seed=42)
    print(Evaluator.report(records))
