import re

class CookingAnimationManager:
    """
    Класс отвечает за автоматическое управление видимостью слоев TMX 
    в зависимости от процесса приготовления.
    """
    def __init__(self):
        self.layers_cache = {}      # Кэш объектов слоев { "gas_stove1": layer_obj }
        self.active_animations = [] # Список активных таймеров

    def refresh_layers_cache(self, tmx_data):
        self.layers_cache = {}
        self.active_animations = []
        
        if not tmx_data:
            return

        prefixes = ("gas_stove", "oven", "sink", "fridge")
        found_layers = []
        
        # ИСПРАВЛЕНИЕ: используем .layers вместо .visible_layers
        for layer in tmx_data.layers:
            if any(layer.name.startswith(p) for p in prefixes):
                self.layers_cache[layer.name] = layer
                layer.visible = False # Прячем, если он был включен в Tiled
                found_layers.append(layer.name)
        
        if found_layers:
            print(f"[AnimationManager] Успешно кэшировано слоев: {found_layers}")
        else:
            print("[AnimationManager] WARNING: No animation layers found in TMX!")

    def start_animation(self, cooking_place_name, animation_type, duration_ms):
        """
        Включает нужный слой на указанное время.
        """
        if animation_type is None:
            return

        # Извлекаем число из имени (cooking_place2 -> 2)
        match = re.search(r'\d+', cooking_place_name)
        if not match:
            return
        
        suffix = match.group()
        # Преобразуем тип (gas-stove -> gas_stove)
        layer_prefix = animation_type.replace("-", "_")
        target_layer_name = f"{layer_prefix}{suffix}"
        
        layer = self.layers_cache.get(target_layer_name)
        if layer:
            layer.visible = True
            # Если на этом месте уже была анимация — замещаем её
            self.active_animations = [a for a in self.active_animations if a['layer_name'] != target_layer_name]
            self.active_animations.append({
                'layer_name': target_layer_name,
                'remaining': duration_ms
            })

    def update(self, dt_ms):
        """
        Обновляет таймеры. Должен вызываться в главном цикле (main.py -> _update).
        """
        finished = []
        for anim in self.active_animations:
            anim['remaining'] -= dt_ms
            if anim['remaining'] <= 0:
                finished.append(anim)
        
        for anim in finished:
            self._stop_animation(anim['layer_name'])

    def _stop_animation(self, layer_name):
        """Выключает слой."""
        if layer_name in self.layers_cache:
            self.layers_cache[layer_name].visible = False
        self.active_animations = [a for a in self.active_animations if a['layer_name'] != layer_name]

    def stop_all(self):
        """Мгновенно выключает всё (при сбросе уровня)."""
        for layer in self.layers_cache.values():
            layer.visible = False
        self.active_animations = []