# core/recipes.py

# Структура: (Инструмент, Текущее_состояние_предмета) -> Результат
RECIPES = {
    # --- КАРТОФЕЛЬ ---
    ("sink", "potato_raw"): {"next_state": "potato_washed", "name": "Мытый картофель", "image": "potato", "time": 2000},
    ("table", "potato_washed"): {"next_state": "potato_cut", "name": "Нарезанный картофель", "image": "potato", "time": 3000},
    ("gas-stove", "potato_cut"): {"next_state": "chips", "name": "Чипсы", "image": "chips", "time": 4000},
    ("oven", "potato_washed"): {"next_state": "potato_baked", "name": "Запеченный картофель", "image": "potato_red", "time": 5000},

    # --- МЯСО ---
    ("sink", "meat_raw"): {"next_state": "meat_washed", "name": "Подготовленное мясо", "image": "meat_raw", "time": 2500},
    ("table", "meat_washed"): {"next_state": "meat_cut", "name": "Мясной нарез", "image": "meat_cut", "time": 3000},
    ("gas-stove", "meat_cut"): {"next_state": "meat_fried", "name": "Жареный стейк", "image": "steak_done", "time": 4500},

    # --- ЯБЛОКИ ---
    ("sink", "apple_raw"): {"next_state": "apple_washed", "name": "Мытое яблоко", "image": "fruit_apple", "time": 1500},
    ("table", "apple_washed"): {"next_state": "apple_cut", "name": "Дольки яблока", "image": "apple_cut", "time": 2000},
    ("oven", "apple_cut"): {"next_state": "apple_pie", "name": "Яблочный пирог", "image": "apple_pie", "time": 6000},

    # --- ТОМАТЫ ---
    ("sink", "tomato_raw"): {"next_state": "tomato_washed", "name": "Чистый томат", "image": "tomato", "time": 1000},
    ("table", "tomato_washed"): {"next_state": "tomato_cut", "name": "Нарезанный томат", "image": "tomato_cut", "time": 2000},
    ("gas-stove", "tomato_cut"): {"next_state": "soup", "name": "Томатный суп", "image": "soup", "time": 4000},

    # --- РЫБА ---
    ("sink", "fish_raw"): {"next_state": "fish_washed", "name": "Чистая рыба", "image": "fish_raw", "time": 2000},
    ("table", "fish_washed"): {"next_state": "fish_cut", "name": "Филе рыбы", "image": "fish_steak", "time": 3000},
    ("table", "fish_cut"): {"next_state": "sashimi", "name": "Сашими", "image": "sashimi", "time": 4000},
}

ALL_PRODUCTS = {
    1: {"name": "potato", "display": "Картофель", "image": "potato"},
    2: {"name": "tomato", "display": "Томат", "image": "tomato"},
    3: {"name": "apple", "display": "Яблоко", "image": "fruit_apple"},
    4: {"name": "meat", "display": "Мясо", "image": "meat_raw"},
    5: {"name": "fish", "display": "Рыба", "image": "fish_raw"},
}

# Ключ заказа должен СОВПАДАТЬ с next_state последнего этапа в RECIPES
FINAL_PRODUCTS = {
    "chips": "Чипсы",
    "potato_baked": "Печеная картошка",
    "apple_pie": "Яблочный пирог",
    "meat_fried": "Мясной стейк",
    "soup": "Томатный суп",
    "sashimi": "Сашими"
}

# Соответствие заказа базовому ингредиенту
STARTING_INGREDIENTS = {
    "chips": ("potato", "Картошка", "potato"),
    "potato_baked": ("potato", "Картошка", "potato"),
    "apple_pie": ("apple", "Яблоко", "fruit_apple"),
    "meat_fried": ("meat", "Мясо", "meat_raw"),
    "soup": ("tomato", "Томат", "tomato"),
    "sashimi": ("fish", "Рыба", "fish_raw")
}

def get_recipe_result(tool_name, item_state):
    return RECIPES.get((tool_name, item_state))