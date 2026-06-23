import pygame

class HumanHandler:  # Проверьте, что имя класса именно HumanHandler
    def __init__(self):
        # Маппинг клавиш для движения
        self.move_keys = {
            pygame.K_w: (0, -1),
            pygame.K_s: (0, 1),
            pygame.K_a: (-1, 0),
            pygame.K_d: (1, 0)
        }
        # Маппинг клавиш для взаимодействия
        self.action_keys = {
            pygame.K_e: "primary",
            pygame.K_f: "secondary"
        }

    def handle_input(self, event, player, level_manager, kitchen_manager, ui_manager):
        """Централизованная обработка ввода игрока."""
        if pygame.time.get_ticks() < player.freeze_until:
            return

        if event.type == pygame.KEYDOWN:
            # 1. Обработка движения
            if event.key in self.move_keys:
                dx, dy = self.move_keys[event.key]
                player.move(dx, dy, level_manager)
            
            # 2. Обработка взаимодействий (E/F)
            elif event.key in self.action_keys:
                action_type = self.action_keys[event.key]
                kitchen_manager.handle_interaction(
                    player, 
                    level_manager, 
                    action_type, 
                    ui_manager
                )