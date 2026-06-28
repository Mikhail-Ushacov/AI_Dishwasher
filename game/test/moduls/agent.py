from core.recipes import get_recipe_result

def get_action_type_for_item(held_item, target_tool_name):
    """
    Определяет, какой тип действия (primary/secondary) нужно отправить в kitchen_manager,
    основываясь на требуемом инструменте из рецепта.
    """
    if not held_item:
        return "primary"

    # 1. Если мы стоим у универсальной точки 'cooking_place'
    if target_tool_name == "cooking_place":
        # Проверяем рецепты для этого предмета
        # Пробуем найти рецепт для плиты
        if get_recipe_result("gas-stove", held_item.state):
            return "primary"  # Газовая плита -> E
        
        # Пробуем найти рецепт для духовки
        if get_recipe_result("oven", held_item.state):
            return "secondary" # Духовка -> F

    # 2. Для всех остальных объектов (fridge, sink, table) всегда используем primary
    return "primary"