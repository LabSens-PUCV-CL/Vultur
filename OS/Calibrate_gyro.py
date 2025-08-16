"""
This script launches a full-screen GUI that triggers gyroscope and accelerometer
calibration on Pixhawk via MAVLink. It guides the user through the required
steps interactively with message boxes.

"""
# Imports
import tkinter as tk
from tkinter import messagebox
from pymavlink import mavutil
import threading
import time

# Function to send calibration commands via MAVLink
def calibrate_sensors():
    try:
# Establish connection with Pixhawk over serial
        master = mavutil.mavlink_connection('/dev/serial0', baud=57600)
        messagebox.showinfo("Connecting", "Waiting for communication with Pixhawk...")
        master.wait_heartbeat(timeout=10)
        messagebox.showinfo("Connected", "Connected to Pixhawk.\n\nPlease place the drone on a flat surface and do not move it.")

# Wait before sending the calibration command
        time.sleep(3)

# Send preflight calibration command (gyro and accelerometer)
        master.mav.command_long_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_CMD_PREFLIGHT_CALIBRATION,
            0,
            1, 1, 0, 0, 0, 0, 0  # Parameters: gyro=1, accel=1, rest=0
        )

# Guide user through accelerometer positioning steps
        steps = [
            "Place the drone upright (normal) and press OK",
            "Place the drone upside down and press OK",
            "Place the drone on its right side and press OK",
            "Place the drone on its left side and press OK",
            "Place the drone nose-up and press OK",
            "Place the drone nose-down and press OK"
        ]

        for step in steps:
            messagebox.showinfo("Accelerometer Calibration", step)
            time.sleep(2)

        messagebox.showinfo("Completed", "Gyroscope and accelerometer calibration completed.")

    except Exception as e:
        messagebox.showerror("Error", f"Calibration failed:\n{e}")

# Function to launch the full-screen GUI
def start_interface():
    root = tk.Tk()
    root.title("Sensor Calibration")
    root.configure(bg="black")
    root.attributes('-fullscreen', True)

# Title label
    label = tk.Label(root, text="Sensor Calibration", font=("Helvetica", 24), fg="white", bg="black")
    label.pack(pady=40)

# Start button - launches calibration in a separate thread
    button = tk.Button(root, text="Start Calibration", font=("Helvetica", 17), bg="green", fg="white", width=16, height=3,
                       command=lambda: threading.Thread(target=calibrate_sensors, daemon=True).start())
    button.pack(pady=15)

# Exit button - exits the application
    exit_button = tk.Button(root, text="Exit", font=("Helvetica", 12), bg="red", fg="white", width=10, height=9,
                            command=root.destroy)
    exit_button.pack(pady=15)

    root.mainloop()

# Run the interface if the script is executed directly
if __name__ == '__main__':
    start_interface()

