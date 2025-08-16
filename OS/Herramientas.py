"""
This script displays a fullscreen graphical menu with buttons to launch different 
Python scripts related to Vultur flight system. Each button opens a different functionality 
(such as flight calculator, sensor calibration, or yaw/pitch/roll display). 

"""

import tkinter as tk
import subprocess

# ───────── Functions to Launch External Scripts ─────────

def open_calculator():
    subprocess.Popen(["python3", "calculadora_vuelo_con_retorno.py"])

def open_calibration():
    subprocess.Popen(["python3", "Calibrate_gyro.py"])

def open_ypr():
    subprocess.Popen(["python3", "mostrar_yaw_pitch_roll.py"])

def close_window():
    root.destroy()

# ───────── GUI Setup ─────────

root = tk.Tk()
root.title("Select Function")
root.configure(bg="black")
root.attributes("-fullscreen", True)

button_font = ("Helvetica", 15)

frame = tk.Frame(root, bg="black")
frame.pack(expand=True)

# ───────── Buttons for Each Function ─────────

tk.Button(frame, text="Flight Calculator", command=open_calculator,
          font=button_font, width=20, height=3, bg="blue", fg="white").pack(pady=10)

tk.Button(frame, text="Sensor Calibration", command=open_calibration,
          font=button_font, width=20, height=3, bg="green", fg="white").pack(pady=10)

tk.Button(frame, text="Yaw Pitch Roll", command=open_ypr,
          font=button_font, width=20, height=3, bg="orange", fg="white").pack(pady=10)

# ───────── Exit Button ─────────

tk.Button(root, text="x", command=close_window,
          font=("Helvetica", 20), bg="red", fg="white", width=2, height=1).place(relx=0.97, rely=0.02, anchor="ne")

# ───────── Start the Main Loop ─────────

root.mainloop()
