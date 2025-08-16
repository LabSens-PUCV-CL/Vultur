"""
This script connects to Pixhawk via MAVLink and displays the Yaw, Pitch,
and Roll values in a fullscreen Tkinter GUI. The values are updated in real time.

"""
# Imports
import tkinter as tk
from pymavlink import mavutil
import threading
import time

# Connect to Pixhawk and start reading ATTITUDE messages
def iniciar_lectura():
    try:
        # Open MAVLink connection via serial
        conexion = mavutil.mavlink_connection('/dev/serial0', baud=57600)
        conexion.wait_heartbeat(timeout=10)  # Wait for heartbeat to confirm connection

        # Background thread to read and update attitude values
        def actualizar_valores():
            while True:
                msg = conexion.recv_match(type='ATTITUDE', blocking=True, timeout=5)
                if msg:
                    roll = round(msg.roll * 57.2958, 1)   # Convert from radians to degrees
                    pitch = round(msg.pitch * 57.2958, 1)
                    yaw = round(msg.yaw * 57.2958, 1)
                    label_yaw.config(text=f"Yaw: {yaw} grados")
                    label_pitch.config(text=f"Pitch: {pitch} grados")
                    label_roll.config(text=f"Roll: {roll} grados")
                time.sleep(0.2)

        # Launch background reader
        threading.Thread(target=actualizar_valores, daemon=True).start()

    except Exception as e:
        label_yaw.config(text=f"Error: {e}")

# Cleanly exit the app and close MAVLink if needed
def salir():
    global mav
    try:
        mav.close()
    except:
        pass
    app.destroy()

# Initialize GUI
app = tk.Tk()
app.title("Lectura en vivo de Yaw, Pitch y Roll")
app.configure(bg='black')
app.attributes('-fullscreen', True)

# Central frame for centering attitude labels
frame = tk.Frame(app, bg='black')
frame.pack(expand=True)

# Yaw label
label_yaw = tk.Label(frame, text="Yaw: -", font=("Helvetica", 24), fg="cyan", bg="black")
label_yaw.pack(pady=10)

# Pitch label
label_pitch = tk.Label(frame, text="Pitch: -", font=("Helvetica", 24), fg="cyan", bg="black")
label_pitch.pack(pady=10)

# Roll label
label_roll = tk.Label(frame, text="Roll: -", font=("Helvetica", 24), fg="cyan", bg="black")
label_roll.pack(pady=10)

# Exit button (top-right corner)
btn_x = tk.Button(app, text="x", command=salir,
                  font=("Helvetica", 20),
                  width=2, height=1,
                  bg="red", fg="white")
btn_x.place(relx=0.97, rely=0.02, anchor="ne")

# Start data reading
iniciar_lectura()

# Run main GUI loop
app.mainloop()
