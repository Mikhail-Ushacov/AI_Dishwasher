import argparse
import os
import pygame
import numpy as np
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

from agent.env import (
    KitchenEnv, build_obs, action_masks,
    ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT,
    ACTION_INTERACT, ACTION_INTERACT_SEC, ACTION_WAIT,
)
from agent.eval import Evaluator
from settings import WIDTH, HEIGHT, FPS, BLACK
from core.entities import Player
from core.level import LevelManager
from core.mechanics import KitchenManager
from visuals.renderer import GameRenderer
from visuals.visual_state import VisualWorldState


class AgentPlayer:
    def __init__(self, model_path: str = "agent/models/ppo_kitchen", map_name: str = "map1.tmx",
                 auto_interact: bool = False):
        self.model_path = model_path
        self.map_name = map_name
        self.auto_interact = auto_interact
        self._model = None

    def _ensure_loaded(self):
        if self._model is None:
            self._model = self._load_model(self.model_path)
        return self._model

    @property
    def model(self):
        return self._ensure_loaded()

    def _load_model(self, path: str) -> MaskablePPO:
        env = KitchenEnv(map_name=self.map_name, auto_interact=self.auto_interact)
        env = ActionMasker(env, lambda e: e.action_masks())
        model = MaskablePPO.load(path, env=env)
        env.close()
        return model

    def act(self, player, kitchen, level):
        model = self.model
        obs = build_obs(player, kitchen, level)
        masks = action_masks(player, level)
        if self.auto_interact and len(masks) >= 5:
            masks = masks[:5]  # only use 5-action masks
        action, _ = model.predict(obs, action_masks=masks, deterministic=True)
        return int(action)


def _parse_args():
    parser = argparse.ArgumentParser(description="Evaluate or view a trained kitchen agent")
    parser.add_argument("--model", type=str, default="agent/models/ppo_kitchen",
                        help="Path to the trained model (without .zip)")
    parser.add_argument("--episodes", type=int, default=10,
                        help="Number of evaluation episodes")
    parser.add_argument("--maps", type=str, nargs="+", default=["map1.tmx"],
                        help="Maps to evaluate on")
    parser.add_argument("--visual", action="store_true",
                        help="Show pygame visualization of the agent playing")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    return parser.parse_args()


def _evaluate_headless(args):
    model_path = f"{args.model}.zip"
    auto_interact = "auto" in args.model
    agent = AgentPlayer(model_path, map_name=args.maps[0], auto_interact=auto_interact)

    evaluator = Evaluator()
    records = evaluator.evaluate(
        agent.model,
        maps=args.maps,
        n_episodes=args.episodes,
        seed=args.seed,
        auto_interact=auto_interact,
    )
    print(Evaluator.report(records))
    return records


def _evaluate_visual(args):
    model_path = f"{args.model}.zip"
    auto_interact = "auto" in args.model
    agent = AgentPlayer(model_path, map_name=args.maps[0], auto_interact=auto_interact)

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("AI Kitchen Agent")
    clock = pygame.time.Clock()

    player = Player()
    level = LevelManager()
    level.load_map(agent.map_name, player, headless=False)
    kitchen = KitchenManager()
    renderer = GameRenderer(screen)

    total_reward = 0.0
    step_count = 0
    done = False

    running = True
    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        if not done:
            action = agent.act(player, kitchen, level)

            if auto_interact:
                if action < 4:
                    dx, dy = [(0, -1), (0, 1), (-1, 0), (1, 0)][action]
                    player.move(dx, dy, level)
                    facing = _get_facing_name_static(player, level)
                    _maybe_interact_static(player, kitchen, level, facing)
                elif action == 4:
                    facing = _get_facing_name_static(player, level)
                    _maybe_interact_static(player, kitchen, level, facing)
            else:
                if action == ACTION_WAIT:
                    pass
                elif action < 4:
                    dx, dy = [(0, -1), (0, 1), (-1, 0), (1, 0)][action]
                    player.move(dx, dy, level)
                elif action in (ACTION_INTERACT, ACTION_INTERACT_SEC):
                    action_type = "primary" if action == ACTION_INTERACT else "secondary"
                    kitchen.handle_interaction(
                        player, level, action_type, pygame.time.get_ticks()
                    )

            step_count += 1

            if step_count >= 3000:
                done = True

        screen.fill(BLACK)
        visual_state = VisualWorldState.from_manual_game(player, kitchen, level)
        renderer.render(visual_state, level)

        font = pygame.font.SysFont(None, 24)
        info_text = f"Step: {step_count}  Score: {kitchen.score}  {'DONE' if done else ''}"
        screen.blit(font.render(info_text, True, (255, 255, 255)), (10, HEIGHT - 30))

        pygame.display.flip()

    pygame.quit()


def _get_facing_name_static(player, level):
    tx, ty = player.cell_x, player.cell_y
    if player.facing == "up": ty -= 1
    elif player.facing == "down": ty += 1
    elif player.facing == "left": tx -= 1
    elif player.facing == "right": tx += 1
    if tx < 0 or tx >= level.width_in_tiles or ty < 0 or ty >= level.height_in_tiles:
        return None
    ts = level.tile_size
    cp = (tx * ts + ts // 2, ty * ts + ts // 2)
    for obj in level.interactive_objects:
        if obj["rect"].collidepoint(cp):
            return obj["name"]
    return None


def _maybe_interact_static(player, kitchen, level, facing):
    if facing is None:
        return None
    held = player.held_item
    if held is None:
        return None if facing != "fridge" else kitchen.handle_interaction(player, level, "primary", 0)
    if held.state == "raw" and facing == "sink":
        return kitchen.handle_interaction(player, level, "primary", 0)
    if held.state == "washed":
        if facing == "table":
            return kitchen.handle_interaction(player, level, "primary", 0)
        if facing == "cooking_place" and kitchen.current_order == "baked":
            return kitchen.handle_interaction(player, level, "secondary", 0)
    if held.state == "cut" and facing in ("cooking_place", "gas-stove"):
        return kitchen.handle_interaction(player, level, "primary", 0)
    if held.state in ("fried", "baked") and facing == "order":
        return kitchen.handle_interaction(player, level, "primary", 0)
    return None


def main():
    args = _parse_args()

    if not os.path.exists(f"{args.model}.zip"):
        print(f"Model not found: {args.model}.zip")
        print("Train a model first: python -m agent.train")
        return

    if args.visual:
        _evaluate_visual(args)
    else:
        _evaluate_headless(args)


if __name__ == "__main__":
    main()
