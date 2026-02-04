from entities import Item

# Словарь всех рецептов в игре
# Формат: "Конечное_состояние": {"display_name": "Название", "steps": [список_состояний]}
RECIPE_BOOK = {
    "fried": {
        "display_name": "Чипсы",
        "image_key": "chips",
        "steps": ["raw", "washed", "cut", "fried"]
    },
    "baked": {
        "display_name": "Печеная картошка",
        "image_key": "potato_red",
        "steps": ["raw", "washed", "baked"]
    }
}

def get_next_state(item, tool_name):
    """Определяет, в какое состояние перейдет предмет при использовании прибора"""
    s = item.state
    
    if tool_name == "sink" and s == "raw":
        return "washed"
    
    if tool_name == "table" and s == "washed":
        return "cut"
    
    if tool_name == "gas-stove" and s == "cut":
        return "fried"
    
    if tool_name == "oven" and s == "washed":
        return "baked"
    
    return None # Если прибор не подходит для этого состояния