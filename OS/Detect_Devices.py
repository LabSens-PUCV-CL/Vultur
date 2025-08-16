"""
This script runs a fullscreen Tkinter GUI on a Raspberry Pi that:
- Detects connected Basler cameras using Pypylon.
- Connects to a Pixhawk via MAVLink to check GPS status and fix.
- Displays system messages in a colored console.
- Uses a common-cathode RGB LED to indicate hardware status:
  - Red blinks if no camera is found.
  - Blue blinks equal to the number of detected cameras.
"""

#Imports
import tkinter as tk
from tkinter import ttk
from pypylon import pylon
from pymavlink import mavutil
import RPi.GPIO as GPIO
import threading
import time

# --- GPIO pin configuration for RGB LED ---
PIN_ROJO = 20
PIN_AZUL = 21
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_ROJO, GPIO.OUT)
GPIO.setup(PIN_AZUL, GPIO.OUT)

# Global MAVLink connection reference
mav = None

# --- LED control functions ---
def apagar_led_rgb():
    GPIO.output(PIN_ROJO, GPIO.LOW)
    GPIO.output(PIN_AZUL, GPIO.LOW)

def encender_color(rojo=False, azul=False):
    GPIO.output(PIN_ROJO, GPIO.HIGH if rojo else GPIO.LOW)
    GPIO.output(PIN_AZUL, GPIO.HIGH if azul else GPIO.LOW)

def parpadear_color(rojo=False, azul=False, veces=3, intervalo=0.3):
    for _ in range(veces):
        encender_color(rojo=rojo, azul=azul)
        time.sleep(intervalo)
        apagar_led_rgb()
        time.sleep(intervalo)

# --- Console printing with color ---
def escribir(texto, color="white"):
    consola.configure(state="normal")
    consola.insert(tk.END, texto + "\n", color)
    consola.configure(state="disabled")
    consola.see(tk.END)

# --- Camera detection logic using Pypylon ---
def detectar_camaras():
    try:
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        if len(devices) == 0:
            escribir("No cameras detected", "red")
            parpadear_color(rojo=True, veces=3)
        else:
            escribir(f"{len(devices)} camera(s) detected:", "green")
            for i, device in enumerate(devices):
                escribir(f"  {i+1}. {device.GetFriendlyName()}", "green")
            parpadear_color(azul=True, veces=len(devices))
    except Exception as e:
        escribir(f"Camera detection error: {e}", "red")
    finally:
        apagar_led_rgb()

# --- GPS detection and fix check using MAVLink ---
def detectar_gps():
    global mav
    try:
        mav = mavutil.mavlink_connection('/dev/serial0', baud=57600)
        mav.wait_heartbeat(timeout=10)
        escribir("GPS heartbeat detected", "cyan")

        msg = mav.recv_match(type='GPS_RAW_INT', blocking=True, timeout=10)
        if msg and msg.fix_type >= 3 and msg.lat not in (0, 0x7FFFFFFF):
            lat = msg.lat / 1e7
            lon = msg.lon / 1e7
            alt = msg.alt / 1000.0
            escribir("GPS Fix acquired", "green")
            escribir(f"Lat: {lat:.7f}, Lon: {lon:.7f}, Alt: {alt:.1f} m", "green")
        else:
            escribir("GPS present but no valid fix", "yellow")
    except Exception as e:
        escribir(f"GPS error: {e}", "red")

# --- Launch both detection processes in separate threads ---
def iniciar_deteccion():
    threading.Thread(target=detectar_camaras, daemon=True).start()
    threading.Thread(target=detectar_gps, daemon=True).start()

# --- Clean exit: close MAVLink and GPIO ---
def cerrar():
    global mav
    try:
        if mav:
            mav.close()
    except:
        pass
    GPIO.cleanup()
    root.destroy()

# === GUI SETUP ===
root = tk.Tk()
root.title("Camera and GPS Detection")
root.configure(bg="black")
root.attributes("-fullscreen", True)

# Exit button in top-right corner
btn_cerrar = tk.Button(root, text="X", command=cerrar,
                       font=("Helvetica", 20), width=2, height=1,
                       bg="red", fg="white", relief="flat")
btn_cerrar.place(relx=0.96, rely=0.02, anchor="ne")

# Main container frame
frame = tk.Frame(root, bg="black", padx=30, pady=30)
frame.pack(fill="both", expand=True, pady=(65, 20))  # space at top for close button

# Console area (Text widget) for log messages
consola = tk.Text(frame, wrap="word", font=("Consolas", 13),
                  bg="black", fg="white", height=30,
                  relief="flat", borderwidth=0, highlightthickness=0)
consola.pack(expand=True, fill="both", pady=10, padx=10)

# Color tag styles for text highlighting
consola.tag_configure("green", foreground="lime")
consola.tag_configure("red", foreground="red")
consola.tag_configure("yellow", foreground="yellow")
consola.tag_configure("cyan", foreground="cyan")
consola.configure(state="disabled")

# Start detection threads
iniciar_deteccion()

# Start main GUI loop
root.mainloop()
