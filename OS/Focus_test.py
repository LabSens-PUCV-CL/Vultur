"""
This script launches a fullscreen GUI for selecting and previewing
the focus quality of connected Basler cameras using Pypylon.

Features:
- Loads exposure and gain settings from config.json.
- Live preview from selected camera.
- Real-time focus metric visualization with colored borders:
    - Green if focus is sharp
    - Red if blurry
- Pressing anywhere on the screen or 'q' exits preview mode.
"""

# --- Imports ---
import tkinter as tk
from tkinter import messagebox
from functools import partial
import cv2, json, os
from pypylon import pylon
import numpy as np

# --- Load camera parameters from config.json ---
EXPOSURE, GAIN = 5000, 0.0
if os.path.exists("config.json"):
    try:
        cfg = json.load(open("config.json"))["Cameras"]
        EXPOSURE = int(cfg.get("ExposureTime", EXPOSURE))
        GAIN     = float(cfg.get("Gain", GAIN))
    except Exception as e:
        print("config.json invalido; usando valores por defecto:", e)

# --- GUI style constants ---
BG_MAIN, FG_MAIN         = "black", "white"
FONT_LABEL               = ("Helvetica", 25)
FONT_BUTTON              = ("Helvetica", 20, "bold")
BTN_BG, BTN_FG           = "gray25", "white"
BTN_ACTIVE_BG, BTN_W     = "gray40", 10

# --- Camera preview and focus evaluation ---
def preview(idx, root):
    """Open camera preview and display real-time focus evaluation."""
    tl   = pylon.TlFactory.GetInstance()
    devs = tl.EnumerateDevices()
    if idx >= len(devs):
        messagebox.showerror("Error", f"Can't find the camera {idx+1}.")
        return

    root.withdraw()  # Hide main window

    # --- Camera setup ---
    cam = pylon.InstantCamera(tl.CreateDevice(devs[idx]))
    cam.Open()
    cam.Width.Value, cam.Height.Value = 1440, 960
    cam.PixelFormat.Value  = "Mono8"
    cam.ExposureTime.Value = EXPOSURE
    cam.Gain.Value         = GAIN
    cam.TriggerMode.Value  = "Off"
    cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    # --- Open fullscreen preview window ---
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
        while not quit_flag:
            res = cam.RetrieveResult(500, pylon.TimeoutHandling_Return)
            if res and res.GrabSucceeded():
                gray = res.Array
                h, w = gray.shape

                # --- Compute focus metric using Sobel ---
                roi = gray[h//3 : 2*h//3, w//3 : 2*w//3]
                gx  = cv2.Sobel(roi, cv2.CV_64F, 1, 0, ksize=3)
                gy  = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=3)
                focus = (gx**2 + gy**2).mean()

                enfocado = focus > 1000  # Threshold for sharpness
                col_bgr = (0, 255, 0) if enfocado else (0, 0, 255)

                # --- Overlay border and text ---
                frame_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                cv2.rectangle(frame_bgr, (5, 5), (w-6, h-6), col_bgr, thickness=40)
                cv2.putText(frame_bgr, f"Foco: {focus:.0f}",
                            (40, 70), cv2.FONT_HERSHEY_SIMPLEX,
                            1.2, col_bgr, 3, cv2.LINE_AA)

                # --- Centering for 480x320 screen ---
                screen_h, screen_w = 320, 480
                fh, fw = frame_bgr.shape[:2]
                top = max(0, (screen_h - fh) // 2)
                bottom = max(0, screen_h - fh - top)
                left = max(0, (screen_w - fw) // 2)
                right = max(0, screen_w - fw - left)
                frame_centered = cv2.copyMakeBorder(frame_bgr, top, bottom, left, right,
                                                    borderType=cv2.BORDER_CONSTANT, value=(0,0,0))

                # --- Show frame ---
                cv2.imshow(win, frame_centered)
                res.Release()

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        # --- Cleanup ---
        if cam.IsGrabbing(): cam.StopGrabbing()
        cam.Close()
        cv2.destroyWindow(win)
        root.deiconify()

# --- GUI main window ---
def main():
    root = tk.Tk()
    root.title("Camera Focus")
    root.configure(bg=BG_MAIN)
    root.attributes("-fullscreen", True)

    # Close button
    barra = tk.Frame(root, bg=BG_MAIN); barra.pack(anchor="ne", padx=20, pady=10)
    tk.Button(barra, text="x",
              command=lambda: root.destroy(),
              font=FONT_LABEL, bg="red", fg="white").pack()

    # Title
    tk.Label(root, text="Choose a camera",
             font=FONT_LABEL, fg=FG_MAIN, bg=BG_MAIN).pack(pady=10)

    # Camera buttons
    cont = tk.Frame(root, bg=BG_MAIN); cont.pack(pady=40)
    for i, txt in enumerate(("CAM 1", "CAM 2")):
        tk.Button(cont, text=txt, width=BTN_W, height=3,
                  font=FONT_BUTTON, bg=BTN_BG, fg=BTN_FG,
                  activebackground=BTN_ACTIVE_BG,
                  command=partial(preview, i, root)).grid(row=0, column=i,
                                                          padx=30, pady=5)

    root.mainloop()

# --- Entry point ---
if __name__ == "__main__":
    main()
