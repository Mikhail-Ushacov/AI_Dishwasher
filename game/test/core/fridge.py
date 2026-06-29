from core.recipes import ALL_PRODUCTS

class FridgeManager:
    def __init__(self):
        self.products = ALL_PRODUCTS
        self.selected_index = 0
        self.is_open = False

    def get_product_by_id(self, product_id):
        return self.products.get(product_id)

    def get_id_by_name(self, name):
        for pid, data in self.products.items():
            if data["name"] == name:
                return pid
        return None

    def toggle(self):
        self.is_open = not self.is_open
        self.selected_index = 0

    def move_selection(self, dx, dy, cols=3):
        rows = (len(self.products) + cols - 1) // cols
        curr_row = self.selected_index // cols
        curr_col = self.selected_index % cols

        new_col = (curr_col + dx) % cols
        new_row = (curr_row + dy) % rows
        
        new_index = new_row * cols + new_col
        if new_index < len(self.products):
            self.selected_index = new_index

    def get_selected_product(self):
        # Возвращает кортеж (id, name) для выбранного индекса
        p_ids = list(self.products.keys())
        selected_id = p_ids[self.selected_index]
        return selected_id, self.products[selected_id]["name"]