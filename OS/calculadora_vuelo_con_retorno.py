"""
This script provides a fullscreen graphical interface to calculate any one of:
altitude, speed, frame rate (FPS), or image overlap — given the other three.
It includes a custom numeric keypad for touchscreen input and is designed for
flight planning.

"""

#Imports
import tkinter as tk
from tkinter import messagebox
import math
from functools import partial

# ---------------- NUMERIC KEYPAD ----------------
# Fullscreen numeric keypad for touchscreen input
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
        entry.delete(0, tk.END)
        entry.insert(0, entrada.get())
        teclado.destroy()
        calculate()  # recalculate when value is inserted

    def cancelar():
        teclado.destroy()

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

    tk.Button(teclado, text="OK", command=confirmar,
              font=("Helvetica", 20), bg="green", fg="white").grid(
        row=5, column=0, columnspan=2, padx=4, pady=8, sticky="nsew"
    )

    tk.Button(teclado, text="Cancel", command=cancelar,
              font=("Helvetica", 20), bg="red", fg="white").grid(
        row=5, column=2, padx=4, pady=8, sticky="nsew"
    )

    for i in range(6):
        teclado.rowconfigure(i, weight=1)
    for j in range(3):
        teclado.columnconfigure(j, weight=1)

# ---------------- FLIGHT CALCULATIONS ----------------
angle_vertical_deg = 20.4
angle_vertical_rad = math.radians(angle_vertical_deg)

def image_height_from_altitude(altitude):
    return 2 * altitude * math.tan(angle_vertical_rad / 2)

def calculate(*args):
    try:
        h_val = altitude_entry.get()
        v_val = velocity_entry.get()
        o_val = overlap_entry.get()
        fps_val = fps_entry.get()

        known_vars = {
            'H': h_val != "",
            'v': v_val != "",
            'O': o_val != "",
            'fps': fps_val != ""
        }

        if list(known_vars.values()).count(True) != 3:
            result_label.config(text="Input 3 variables.")
            return

        h_val = float(h_val) if h_val else None
        v_val = float(v_val) if v_val else None
        o_val = float(o_val) / 100 if o_val else None
        fps_val = float(fps_val) if fps_val else None

        result = ""

        if not known_vars['H']:
            h_terreno = v_val / (fps_val * (1 - o_val))
            h = h_terreno / (2 * math.tan(angle_vertical_rad / 2))
            result = f"Altitude required: {h:.2f} m"
        elif not known_vars['v']:
            h_terreno = image_height_from_altitude(h_val)
            v = fps_val * h_terreno * (1 - o_val)
            result = f"Speed required: {v:.2f} m/s"
        elif not known_vars['O']:
            h_terreno = image_height_from_altitude(h_val)
            o = 1 - v_val / (fps_val * h_terreno)
            result = f"Overlay required: {o * 100:.2f} %"
        elif not known_vars['fps']:
            h_terreno = image_height_from_altitude(h_val)
            fps = v_val / (h_terreno * (1 - o_val))
            result = f"FPS required: {fps:.2f}"
        else:
            result = "Unexpected error."

        result_label.config(text=result)
    except Exception as e:
        messagebox.showerror("Error", f"Check the inputs.\n\n{e}")

def cerrar_ventana():
    root.destroy()

# ---------------- GUI INTERFACE ----------------
root = tk.Tk()
root.title("Flight Calculator")
root.configure(bg='black')
root.attributes('-fullscreen', True)

font_label = ("Helvetica", 16)
font_entry = ("Helvetica", 16)
font_result = ("Helvetica", 17, "bold")

# Close button (top right corner)
boton_frame = tk.Frame(root, bg='black')
boton_frame.pack(anchor='ne', padx=20, pady=10)
tk.Button(boton_frame, text="x", command=cerrar_ventana,
          font=("Helvetica", 20), width=2, height=1,
          bg="red", fg="white").pack()

# Title label (can be used for messages)
tk.Label(root, text="", font=("helvetica",10,"bold"),
         fg="white", bg="black").pack(pady=10)

frame_inputs = tk.Frame(root, bg='black')
frame_inputs.pack()

# Input fields
def add_input_row(text, row, var_ref):
    tk.Label(frame_inputs, text=text, font=font_label, fg="white", bg="black").grid(
        row=row, column=0, sticky="e", padx=10, pady=5)
    entry = tk.Entry(frame_inputs, font=font_entry, width=10)
    entry.grid(row=row, column=1, padx=10, pady=5)
    entry.bind("<KeyRelease>", calculate)
    entry.bind("<Button-1>", partial(mostrar_teclado, entry))
    var_ref.append(entry)

altitude_entry_ref = []
velocity_entry_ref = []
overlap_entry_ref = []
fps_entry_ref = []

add_input_row("Altitude (m):", 0, altitude_entry_ref)
add_input_row("Speed (m/s):", 1, velocity_entry_ref)
add_input_row("Overlay (%):", 2, overlap_entry_ref)
add_input_row("FPS:", 3, fps_entry_ref)

altitude_entry = altitude_entry_ref[0]
velocity_entry = velocity_entry_ref[0]
overlap_entry = overlap_entry_ref[0]
fps_entry = fps_entry_ref[0]

# Result label
result_label = tk.Label(root, text="", font=font_result, fg="cyan", bg="black")
result_label.pack(pady=20)

# Start main GUI loop
root.mainloop()
