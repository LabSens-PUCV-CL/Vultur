"""
This script displays a fullscreen Tkinter interface to configure camera parameters 
such as Exposure Time, Gain, and FPS.
- Values are saved to `config.json` file.
- Touchscreen-compatible numeric keypad is provided for input.
- Includes close and save buttons for a user-friendly experience.

"""

# Imports
import tkinter as tk
from tkinter import messagebox
import json
import os
from functools import partial

CONFIG_FILE = "config.json"  # File to store the configuration values

# Load configuration from file if it exists
def cargar_configuracion():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    return {}

# Save current configuration to file
def guardar_configuracion():
    nueva_config = {
        "Cameras": {
            "ExposureTime": int(entry_exposure1.get()),
            "Gain": float(entry_gain1.get()),
            "FPS": float(entry_fps1.get())
        }
    }

    with open(CONFIG_FILE, "w") as file:
        json.dump(nueva_config, file, indent=4)

    messagebox.showinfo("Saved", "Saved succesfully.")

# Close the window and return to the main interface
def regresar_interfaz():
    root.destroy()

# Fullscreen numeric keypad for entering values on touch screen
def mostrar_teclado(entry, event=None):
    teclado = tk.Toplevel(root)
    teclado.attributes('-fullscreen', True)
    teclado.configure(bg="black")

    entrada = tk.StringVar(value=entry.get())

    entry_box = tk.Entry(teclado, textvariable=entrada, font=("Helvetica", 26), justify='right')
    entry_box.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

    def agregar(caracter):
        entrada.set(entrada.get() + caracter)

    def borrar():
        entrada.set(entrada.get()[:-1])

    def confirmar():
        try:
            entry.delete(0, tk.END)
            entry.insert(0, entrada.get())
        except Exception as e:
            print("Input mistake:", e)
        teclado.destroy()

    def cancelar():
        teclado.destroy()

    # Layout for numeric buttons
    botones = [
        ('7', 1, 0), ('8', 1, 1), ('9', 1, 2),
        ('4', 2, 0), ('5', 2, 1), ('6', 2, 2),
        ('1', 3, 0), ('2', 3, 1), ('3', 3, 2),
        ('.', 4, 0), ('0', 4, 1), ('←', 4, 2),
    ]

    for texto, fila, col in botones:
        cmd = borrar if texto == '←' else lambda t=texto: agregar(t)
        tk.Button(teclado, text=texto, command=cmd,
                  font=("Helvetica", 24), bg="gray20", fg="white").grid(
            row=fila, column=col, padx=4, pady=4, sticky="nsew"
        )

    # OK and Cancel buttons
    tk.Button(teclado, text="OK", command=confirmar,
              font=("Helvetica", 20), bg="green", fg="white").grid(
        row=5, column=0, columnspan=2, padx=4, pady=8, sticky="nsew"
    )

    tk.Button(teclado, text="Cancel", command=cancelar,
              font=("Helvetica", 20), bg="red", fg="white").grid(
        row=5, column=2, padx=4, pady=8, sticky="nsew"
    )

    # Configure grid resizing
    for i in range(6):
        teclado.rowconfigure(i, weight=1)
    for j in range(3):
        teclado.columnconfigure(j, weight=1)

# Load config and start GUI
config = cargar_configuracion()

# Setup main window
root = tk.Tk()
root.title("Camera settings")
root.configure(bg="black")
root.attributes('-fullscreen', True)

# Fonts and colors
font_label = ("Helvetica", 22)
font_entry = ("Helvetica", 16)
font_button = ("Helvetica", 14, "bold")
label_fg = "white"
entry_bg = "gray20"
entry_fg = "white"
button_bg = "gray30"
button_fg = "white"

# Close button (top right corner)
boton_frame = tk.Frame(root, bg='black')
boton_frame.pack(anchor='ne', padx=20, pady=10)
tk.Button(boton_frame, text="x", command=regresar_interfaz, font=font_label, bg="red", fg="white").pack()

# Inputs frame
frame_inputs = tk.Frame(root, bg='black')
frame_inputs.pack()

# Parameters and input entries
parametros = ["ExposureTime", "Gain", "FPS"]
entries_c1 = []

for i, param in enumerate(parametros):
    tk.Label(frame_inputs, text=f"{param}:", font=font_label, fg=label_fg, bg="black").grid(
        row=i, column=0, sticky="e", padx=10, pady=5)
    entry = tk.Entry(frame_inputs, width=8, font=font_entry, bg=entry_bg, fg=entry_fg, insertbackground="white")
    entry.grid(row=i, column=1, padx=10, pady=5)
    entry.insert(0, config.get("Cameras", {}).get(param.replace(" ", ""), ""))
    entry.bind("<Button-1>", partial(mostrar_teclado, entry))  # Show keypad when clicked
    entries_c1.append(entry)

# Unpack entries into individual variables
entry_exposure1, entry_gain1, entry_fps1 = entries_c1

# Save button
tk.Button(root, text="Save settings", command=guardar_configuracion,
          bg="green", height=2, fg=button_fg, font=("helvetica", 16, "bold")).pack(pady=23)

# Run GUI
root.mainloop()
