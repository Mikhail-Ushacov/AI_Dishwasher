"""Kitchen graph renderer for visualizing the environment."""

import pygame
import math
from typing import Dict, Optional, List

from .sprite_manager import SpriteManager


class KitchenRenderer:
    """Renders the kitchen environment state."""
    
    def __init__(self, screen: pygame.Surface, config: dict, sprite_manager: SpriteManager):
        """
        Initialize the renderer.
        
        Args:
            screen: Pygame surface to render to
            config: Visualization configuration
            sprite_manager: Sprite manager for assets
        """
        self.screen = screen
        self.config = config
        self.sprite_manager = sprite_manager
        
        # Extract configs
        self.layout = config['layout']
        self.stations_config = config['stations']
        self.edges_config = config['edges']
        self.ui_config = config['ui']
        self.agent_config = config['agent']
        self.inventory_config = config['inventory']
        self.orders_config = config['orders']
        
        # Font setup
        pygame.font.init()
        self.font = pygame.font.SysFont(
            self.ui_config['font_family'],
            self.ui_config['font_size']
        )
        self.header_font = pygame.font.SysFont(
            self.ui_config['font_family'],
            self.ui_config['header_font_size']
        )
        
    def render(self, state: dict, current_tick: int):
        """
        Render the current state.
        
        Args:
            state: Current world state snapshot
            current_tick: Current simulation tick
        """
        # Draw edges (connections between nodes)
        self._draw_edges()
        
        # Draw stations (nodes)
        self._draw_stations(state)
        
        # Draw agent
        self._draw_agent(state)
        
        # Draw HUD (heads-up display)
        self._draw_hud(state, current_tick)
        
        # Draw orders panel
        self._draw_orders_panel(state)
        
        # Draw inventory panel
        self._draw_inventory_panel(state)
        
    def _draw_edges(self):
        """Draw connections between nodes."""
        edge_color = self._hex_to_rgb(self.edges_config['color'])
        edge_width = self.edges_config['width']
        
        # Get all edges from layout
        # For now, we draw edges based on typical kitchen layout
        # In a full implementation, edges would come from state or config
        edges = [
            (0, 1),  # Floor to PotatoBin
            (0, 2),  # Floor to TomatoBin
            (0, 3),  # Floor to Stove
            (0, 4),  # Floor to CutBoard
            (3, 5),  # Stove to Service
            (4, 5),  # CutBoard to Service
            (1, 3),  # PotatoBin to Stove
            (2, 4),  # TomatoBin to CutBoard
        ]
        
        for from_node, to_node in edges:
            if from_node in self.layout['nodes'] and to_node in self.layout['nodes']:
                from_pos = self._get_node_center(from_node)
                to_pos = self._get_node_center(to_node)
                
                pygame.draw.line(
                    self.screen,
                    edge_color,
                    from_pos,
                    to_pos,
                    edge_width
                )
                
    def _draw_stations(self, state: dict):
        """Draw all stations/nodes."""
        stations = state.get('stations', {})
        
        for node_id, node_config in self.layout['nodes'].items():
            pos = (node_config['x'], node_config['y'])
            station_state = stations.get(str(node_id), {})
            
            # Determine station type
            station_type = station_state.get('station_type', 'floor')
            if not station_type and 'type' in node_config:
                # Fallback to layout config
                station_type = self._get_station_type_from_layout(node_id)
                
            # Get station config
            station_cfg = self.stations_config.get(station_type, self.stations_config['floor'])
            
            # Draw station circle
            color = self._hex_to_rgb(station_cfg['base_color'])
            size = station_cfg['size']
            
            # Check if busy (pulse effect)
            is_busy = station_state.get('is_busy', False)
            if is_busy:
                highlight = self._hex_to_rgb(station_cfg['highlight_color'])
                # Draw pulsing ring
                pygame.draw.circle(self.screen, highlight, pos, size + 5, 3)
                
            pygame.draw.circle(self.screen, color, pos, size)
            pygame.draw.circle(self.screen, (0, 0, 0), pos, size, 2)
            
            # Draw station label
            label = node_config.get('label', f'Station {node_id}')
            text_surface = self.font.render(label, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(pos[0], pos[1] - size - 15))
            self.screen.blit(text_surface, text_rect)
            
            # Draw held item if any
            held_item = station_state.get('held_item')
            if held_item:
                self._draw_item_at_position(held_item, pos, size * 0.6)
                
            # Draw progress bar if busy
            if is_busy:
                timer = station_state.get('timer', 0)
                self._draw_progress_bar(pos[0], pos[1] + size + 10, timer, 100)
                
    def _draw_agent(self, state: dict):
        """Draw the agent character."""
        agent_node = state.get('agent_node', 0)
        
        if agent_node in self.layout['nodes']:
            pos = self._get_node_center(agent_node)
            
            # Try to load agent sprite
            agent_sprite = self.sprite_manager.get_agent_sprite()
            
            if agent_sprite:
                # Scale and draw sprite
                size = self.agent_config['size'] * 2
                scaled = pygame.transform.scale(agent_sprite, (size, size))
                rect = scaled.get_rect(center=pos)
                self.screen.blit(scaled, rect)
            else:
                # Fallback: draw colored circle
                color = self._hex_to_rgb(self.agent_config['color'])
                size = self.agent_config['size']
                pygame.draw.circle(self.screen, color, pos, size)
                pygame.draw.circle(self.screen, (0, 0, 0), pos, size, 2)
                
    def _draw_hud(self, state: dict, current_tick: int):
        """Draw heads-up display (time, score, etc.)."""
        # Draw time
        time_text = f"Tick: {current_tick}"
        text_surface = self.header_font.render(time_text, True, (255, 255, 255))
        self.screen.blit(text_surface, (10, 10))
        
        # Draw active order count
        orders = state.get('orders', [])
        orders_text = f"Active Orders: {len(orders)}"
        text_surface = self.header_font.render(orders_text, True, (255, 255, 255))
        self.screen.blit(text_surface, (10, 40))
        
        # Draw completed orders
        completed = state.get('completed_orders', 0)
        completed_text = f"Completed: {completed}"
        text_surface = self.header_font.render(completed_text, True, (0, 255, 0))  # Green color
        self.screen.blit(text_surface, (10, 70))
        
    def _draw_orders_panel(self, state: dict):
        """Draw the orders panel on the right side."""
        panel_x = self.screen.get_width() - self.orders_config['panel_width'] - 10
        panel_y = 100
        panel_width = self.orders_config['panel_width']
        
        # Draw panel background
        panel_color = self._hex_to_rgb(self.ui_config['panel_color'])
        pygame.draw.rect(self.screen, panel_color, (panel_x, panel_y, panel_width, 300))
        
        # Draw header
        header_text = "Active Orders"
        text_surface = self.header_font.render(header_text, True, (255, 255, 255))
        self.screen.blit(text_surface, (panel_x + 10, panel_y + 10))
        
        # Draw orders
        orders = state.get('orders', [])
        y_offset = panel_y + 50
        
        for order in orders:
            order_id = order.get('order_id', 0)
            item_type = order.get('item_type', 0)
            time_remaining = order.get('time_remaining', 0)
            max_time = order.get('max_time', 60)
            
            # Draw order item icon
            item_pos = (panel_x + 20, y_offset)
            self._draw_item_at_position({'type_id': item_type}, item_pos, 25)
            
            # Draw TTL bar
            bar_width = panel_width - 60
            progress = time_remaining / max_time if max_time > 0 else 0
            self._draw_progress_bar(
                panel_x + 50,
                y_offset + 10,
                time_remaining,
                max_time,
                width=bar_width
            )
            
            y_offset += 50
            
    def _draw_inventory_panel(self, state: dict):
        """Draw the inventory panel at the bottom."""
        panel_x = 10
        panel_y = self.screen.get_height() - 80
        
        # Draw header
        header_text = "Inventory"
        text_surface = self.header_font.render(header_text, True, (255, 255, 255))
        self.screen.blit(text_surface, (panel_x, panel_y))
        
        # Draw inventory slots
        inventory = state.get('inventory', [])
        max_slots = self.inventory_config['max_slots']
        slot_size = self.inventory_config['slot_size']
        slot_spacing = self.inventory_config['slot_spacing']
        
        for i in range(max_slots):
            slot_x = panel_x + i * (slot_size + slot_spacing)
            slot_y = panel_y + 30
            
            # Draw slot background
            bg_color = self._hex_to_rgb(self.inventory_config['background'])
            border_color = self._hex_to_rgb(self.inventory_config['border_color'])
            
            pygame.draw.rect(
                self.screen,
                bg_color,
                (slot_x, slot_y, slot_size, slot_size)
            )
            pygame.draw.rect(
                self.screen,
                border_color,
                (slot_x, slot_y, slot_size, slot_size),
                self.inventory_config['border_width']
            )
            
            # Draw item if present
            if i < len(inventory):
                item = inventory[i]
                item_pos = (slot_x + slot_size // 2, slot_y + slot_size // 2)
                self._draw_item_at_position(item, item_pos, slot_size * 0.7)
                
    def _draw_item_at_position(self, item: dict, pos: tuple, size: float):
        """Draw an item sprite at the given position."""
        item_id = item.get('type_id', 0)
        
        # Get sprite
        sprite = self.sprite_manager.get_sprite(item_id)
        
        if sprite:
            # Scale and draw
            scaled_size = int(size)
            scaled = pygame.transform.scale(sprite, (scaled_size, scaled_size))
            rect = scaled.get_rect(center=pos)
            self.screen.blit(scaled, rect)
        else:
            # Fallback: draw colored square
            color = self._hex_to_rgb(self.sprite_manager.get_item_color(item_id))
            rect = pygame.Rect(0, 0, int(size), int(size))
            rect.center = pos
            pygame.draw.rect(self.screen, color, rect)
            
    def _draw_progress_bar(self, x: int, y: int, current: int, maximum: int, width: int = 100):
        """Draw a progress bar."""
        bar_height = self.ui_config['progress_bar']['height']
        
        # Background
        bg_color = self._hex_to_rgb(self.ui_config['progress_bar']['background'])
        pygame.draw.rect(self.screen, bg_color, (x, y, width, bar_height))
        
        # Progress fill
        if maximum > 0:
            progress = current / maximum
            progress_width = int(width * progress)
            
            # Choose color based on progress
            if progress < 0.2:
                color = self._hex_to_rgb(self.ui_config['progress_bar']['danger_color'])
            elif progress < 0.5:
                color = self._hex_to_rgb(self.ui_config['progress_bar']['warning_color'])
            else:
                color = self._hex_to_rgb(self.ui_config['progress_bar']['fill_color'])
                
            pygame.draw.rect(self.screen, color, (x, y, progress_width, bar_height))
            
        # Border
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, width, bar_height), 1)
        
    def _get_node_center(self, node_id: int) -> tuple:
        """Get the center position of a node."""
        node_config = self.layout['nodes'].get(node_id, {})
        return (node_config.get('x', 0), node_config.get('y', 0))
        
    def _get_station_type_from_layout(self, node_id: int) -> str:
        """Infer station type from node ID based on default layout."""
        # Default mapping from node IDs to types
        type_map = {
            0: 'floor',
            1: 'source',
            2: 'source',
            3: 'process',
            4: 'process',
            5: 'delivery'
        }
        return type_map.get(node_id, 'floor')
        
    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 8:  # RGBA
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        else:  # RGB
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
