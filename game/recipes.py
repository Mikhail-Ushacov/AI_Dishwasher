from entities import Item

# Описание процессов: Инструмент -> (Исходное состояние -> (Новое состояние, Название, Ключ_картинки, Время_сек))
PROCESSES = {
    "sink": {
        "raw": {"next_state": "washed", "name": "Помытая картошка", "image": "potato", "time": 3000}
    },
    "table": {
        "washed": {"next_state": "cut", "name": "Нарезанная картошка", "image": "potato", "time": 3000}
    },
    "gas-stove": {
        "cut": {"next_state": "fried", "name": "Чипсы", "image": "chips", "time": 4000}
    },
    "oven": {
        "washed": {"next_state": "baked", "name": "Печеная картошка", "image": "potato_red", "time": 5000}
    }
}

def get_recipe_result(tool_name, item_state):
    """Возвращает параметры трансформации или None, если действие невозможно"""
    tool = PROCESSES.get(tool_name)
    if tool and item_state in tool:
        return tool[item_state]
    return None