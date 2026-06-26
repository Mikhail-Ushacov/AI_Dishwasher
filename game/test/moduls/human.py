import pygame
from typing import Optional
from core.mechanics import InteractionResult


class HumanHandler:
    def __init__(self):
        self.move_keys = {
            pygame.K_w: (0, -1),
            pygame.K_s: (0, 1),
            pygame.K_a: (-1, 0),
            pygame.K_d: (1, 0)
        }
        self.action_keys = {
            pygame.K_e: "primary",
            pygame.K_f: "secondary"
        }

    def handle_input(self, event, player, level_manager, kitchen_manager) -> Optional[InteractionResult]:
        now = pygame.time.get_ticks()

        if now < player.freeze_until:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key in self.move_keys:
                dx, dy = self.move_keys[event.key]
                player.move(dx, dy, level_manager)
                return None

            elif event.key in self.action_keys:
                action_type = self.action_keys[event.key]
                return kitchen_manager.handle_interaction(
                    player,
                    level_manager,
                    action_type,
                    now
                )

        return None
