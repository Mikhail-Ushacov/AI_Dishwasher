import tkinter as tk
import subprocess
import sys
import os

def launch_game():
    # путь: app/launcher.py → ../game/main.py
    base_dir = os.path.dirname(__file__)
    game_path = os.path.join(base_dir, "..", "game", "main.py")

    subprocess.Popen([sys.executable, game_path])

root = tk.Tk()
root.title("AI Dishwasher Launcher")
root.geometry("800x500")

# Левая часть — зона приложения
app_frame = tk.Frame(root, bg="#222")
app_frame.pack(side="left", fill="both", expand=True)

label = tk.Label(
    app_frame,
    text="Здесь будет запускаться игра",
    fg="white",
    bg="#222",
    font=("Arial", 14)
)
label.place(relx=0.5, rely=0.5, anchor="center")

# Правая панель
control_frame = tk.Frame(root, width=250)
control_frame.pack(side="right", fill="y")

tk.Label(
    control_frame,
    text="Панель управления",
    font=("Arial", 12)
).pack(pady=15)

tk.Button(
    control_frame,
    text="Запустить игру",
    command=launch_game
).pack(pady=10)

tk.Button(
    control_frame,
    text="Кнопка 1"
).pack(pady=10)

tk.Button(
    control_frame,
    text="Кнопка 2"
).pack(pady=10)

root.mainloop()
