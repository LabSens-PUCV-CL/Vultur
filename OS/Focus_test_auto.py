"""
This script provides a fullscreen GUI for manual and automatic focus control 
of camera lenses using a servo motor.

Features:
- Detects connected Basler cameras using Pypylon.
- Displays a live preview from the selected camera.
- Performs coarse and fine autofocus sweep using a focus metric.
- Allows manual focus adjustment via servo buttons.
- Reads and applies exposure and gain from `config.json`.

"""

# --- Imports ---
import tkinter as tk
from tkinter import messagebox
from functools import partial
import cv2, json, os
from pypylon import pylon
import numpy as np
import RPi.GPIO as GPIO
import time

# --- Load camera parameters from config file ---
EXPOSURE, GAIN = 5000, 0.0  # Defaults
if os.path.exists("config.json"):
    try:
        cfg = json.load(open("config.json"))["Cameras"]
        EXPOSURE = int(cfg.get("ExposureTime", EXPOSURE))
        GAIN     = float(cfg.get("Gain", GAIN))
    except Exception as e:
        print("config.json invalido; usando valores por defecto:", e)

# --- Servo motor configuration ---
SERVO_GPIO = 5
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_GPIO, GPIO.OUT)
servo = GPIO.PWM(SERVO_GPIO, 50)  # 50 Hz PWM for servo
servo.start(0)
current_angle = 90  # Initial position (arbitrary)
servo_step = 5      # Degrees to move per step
AUTOFOCUS_MARGIN = 0.93
AUTOFOCUS_STEP = 4
mejor_focus = 0
focus_map = []  # Stores (angle, focus_metric)

# --- Servo movement helpers ---
def move_servo_to(angle):
    """Move the servo to the specified angle."""
    angle = max(0, min(180, angle))
    duty = 2.5 + (angle / 18)
    servo.ChangeDutyCycle(duty)
    time.sleep(0.3)
    servo.ChangeDutyCycle(0)

def servo_enfocar():
    """Increase lens focus (servo forward)."""
    global current_angle
    current_angle = min(180, current_angle + servo_step)
    move_servo_to(current_angle)

def servo_desenfocar():
    """Decrease lens focus (servo backward)."""
    global current_angle
    current_angle = max(0, current_angle - servo_step)
    move_servo_to(current_angle)

# --- GUI Style Constants ---
BG_MAIN, FG_MAIN         = "black", "white"
FONT_LABEL               = ("Helvetica", 25)
FONT_BUTTON              = ("Helvetica", 20, "bold")
BTN_BG, BTN_FG           = "gray25", "white"
BTN_ACTIVE_BG, BTN_W     = "gray40", 10

# --- Camera preview and autofocus logic ---
def preview(idx, root):
    """Open camera preview and perform autofocus routine."""
    tl   = pylon.TlFactory.GetInstance()
    devs = tl.EnumerateDevices()
    if idx >= len(devs):
        messagebox.showerror("Error", f"Can't find the camera {idx+1}.")
        return

    root.withdraw()

    cam = pylon.InstantCamera(tl.CreateDevice(devs[idx]))
    cam.Open()
    cam.Width.Value, cam.Height.Value = 1440, 960
    cam.PixelFormat.Value  = "Mono8"
    cam.ExposureTime.Value = EXPOSURE
    cam.Gain.Value         = GAIN
    cam.TriggerMode.Value  = "Off"
    cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    win = f"CAM {idx+1} - Enfoque (toque para salir)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    quit_flag = False

    def on_mouse(event, x, y, flags, param):
        nonlocal quit_flag
        if event == cv2.EVENT_LBUTTONDOWN:
            quit_flag = True

    cv2.setMouseCallback(win, on_mouse)

    try:
        global mejor_focus, current_angle
        mejor_focus = 0
        focus_map = []

        # --- Coarse scan: test from 0° to 180° every 15° ---
        for angulo in range(0, 181, 15):
            current_angle = angulo
            move_servo_to(current_angle)
            time.sleep(0.5)
            res = cam.RetrieveResult(500, pylon.TimeoutHandling_Return)
            if res and res.GrabSucceeded():
                gray = res.Array
                h, w = gray.shape
                roi = gray[h//3 : 2*h//3, w//3 : 2*w//3]
                gx = cv2.Sobel(roi, cv2.CV_64F, 1, 0, ksize=3)
                gy = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=3)
                focus = (gx**2 + gy**2).mean()
                focus_map.append((angulo, focus))

                # Display current focus measure
                frame_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                cv2.putText(frame_bgr, f"Scan: {angulo} deg  Foco: {focus:.0f}",
                            (30, 60), cv2.FONT_HERSHEY_SIMPLEX,
                            1.0, (255, 255, 0), 2, cv2.LINE_AA)

                frame_resized = cv2.resize(frame_bgr, (480, 320))
                cv2.imshow(win, frame_resized)
                cv2.waitKey(1)
                res.Release()

        # --- Fine scan around the best coarse angle ---
        if focus_map:
            best_angle_coarse, mejor_focus = max(focus_map, key=lambda x: x[1])
            fine_start = max(0, best_angle_coarse - 15)
            fine_end = min(180, best_angle_coarse + 15)
            focus_map_fine = []

            for angulo in range(fine_start, fine_end + 1, 5):
                current_angle = angulo
                move_servo_to(current_angle)
                time.sleep(0.5)
                res = cam.RetrieveResult(500, pylon.TimeoutHandling_Return)
                if res and res.GrabSucceeded():
                    gray = res.Array
                    h, w = gray.shape
                    roi = gray[h//3 : 2*h//3, w//3 : 2*w//3]
                    gx = cv2.Sobel(roi, cv2.CV_64F, 1, 0, ksize=3)
                    gy = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=3)
                    focus = (gx**2 + gy**2).mean()
                    focus_map_fine.append((angulo, focus))

                    frame_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                    cv2.putText(frame_bgr, f"Fine: {angulo} deg  Foco: {focus:.0f}",
                                (30, 60), cv2.FONT_HERSHEY_SIMPLEX,
                                1.0, (0, 255, 255), 2, cv2.LINE_AA)

                    frame_resized = cv2.resize(frame_bgr, (480, 320))
                    cv2.imshow(win, frame_resized)
                    cv2.waitKey(1)
                    res.Release()

            # Set best fine angle
            if focus_map_fine:
                best_angle, mejor_focus = max(focus_map_fine, key=lambda x: x[1])
                current_angle = best_angle
                move_servo_to(current_angle)

        # Cleanup
        cam.Close()
        if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) >= 1:
            cv2.destroyWindow(win)
        root.deiconify()
        servo.ChangeDutyCycle(0)

    finally:
        if cam.IsGrabbing(): cam.StopGrabbing()
        cam.Close()
        if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) >= 1:
            cv2.destroyWindow(win)
            root.deiconify()
            servo.ChangeDutyCycle(0)

# --- GUI Main ---
def main():
    root = tk.Tk()
    root.title("Camera Focus")
    root.configure(bg="black")
    root.attributes("-fullscreen", True)

    # Close button
    barra = tk.Frame(root, bg="black"); barra.pack(anchor="ne", padx=20, pady=10)
    tk.Button(barra, text="x",
              command=lambda: (GPIO.cleanup(), root.destroy()),
              font=("Helvetica", 25), bg="red", fg="white").pack()

    # Camera selection
    tk.Label(root, text="Choose a camera",
             font=("Helvetica", 25), fg="white", bg="black").pack(pady=10)

    cont = tk.Frame(root, bg="black"); cont.pack(pady=20)
    for i, txt in enumerate(("CAM 1", "CAM 2")):
        tk.Button(cont, text=txt, width=10, height=3,
                  font=("Helvetica", 20, "bold"), bg="gray25", fg="white",
                  activebackground="gray40",
                  command=partial(preview, i, root)).grid(row=0, column=i, padx=30, pady=5)

    # Manual focus control buttons
    foco_frame = tk.Frame(root, bg="black")
    foco_frame.pack(pady=30)
    tk.Label(foco_frame, text="Control de enfoque", font=("Helvetica", 25),
             fg="white", bg="black").pack(pady=5)

    btns = tk.Frame(foco_frame, bg="black")
    btns.pack()

    tk.Button(btns, text="🔼 Enfocar", width=10, height=2,
              font=("Helvetica", 20, "bold"), bg="gray25", fg="white",
              activebackground="gray40",
              command=servo_enfocar).grid(row=0, column=0, padx=20)

    tk.Button(btns, text="🔽 Desenfocar", width=10, height=2,
              font=("Helvetica", 20, "bold"), bg="gray25", fg="white",
              activebackground="gray40",
              command=servo_desenfocar).grid(row=0, column=1, padx=20)

    root.mainloop()

# --- Entry point ---
if __name__ == "__main__":
    main()
