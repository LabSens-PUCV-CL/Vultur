"""
This script creates a full-screen GUI interface for controlling the main system of Vultur.
It includes buttons to:
- Detect connected devices,
- Configure camera parameters,
- Preview a live view for focus,
- Start and stop image capture (with GPIO support),
- Launch additional tools.

The interface includes a green flashing border to indicate active capture, GPIO-based shutdown handling,
and an auto-hiding console window for displaying subprocess outputs in real time.

"""
#Imports
import tkinter as tk
from tkinter import messagebox, Toplevel
import subprocess
import threading
import sys
import signal
import RPi.GPIO as GPIO
import os
import time

AUTOHIDE_DELAY_MS = 10000  # Delay to hide the console window (ms)

class InterfaceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Execution Interface")
        self.capture_process = None
        self.console_window = None
        self.console_text = None
        self.hide_timer = None
        self.shutdown_timer = None
        self.shutdown_msg_timer = None
        self.shutdown_popup = None
        self.animation_active = False
        self.shutdown_hold_time = 3000  # Time to hold button to trigger shutdown (ms)
        self.green_frames = []
        self.blinking_active = False

        self.root.configure(bg='black')
        self.root.attributes('-fullscreen', True)
        self.is_fullscreen = True

        # Create main button frame
        self.button_frame = tk.Frame(root, bg='black')
        self.button_frame.pack(pady=20)

        # Define button labels, functions and colors
        buttons = [
            ("Detect Devices", self.detect_devices, "purple"),
            ("Configure Cameras", self.open_config, "blue"),
            ("Live View", self.capture_and_preview, "blue"),
            ("Tools", self.open_tools, "orange"),
            ("Start Capture", self.start_capture, "green"),
            ("Stop Capture", self.stop_capture, "red")
        ]

        # Create buttons in 2 columns
        for i, (text, command, color) in enumerate(buttons):
            tk.Button(self.button_frame, text=text, command=command, height=5, width=25,
                      bg=color, fg='white', font=("Helvetica", 10, "bold")).grid(row=i // 2, column=i % 2, padx=5, pady=5)

        # Redirect stdout to GUI
        sys.stdout = self

        # Setup GPIO for physical buttons
        GPIO.setmode(GPIO.BCM)
        self.pin_start = 19
        self.pin_stop  = 26
        GPIO.setup(self.pin_start, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.pin_stop,  GPIO.IN, pull_up_down=GPIO.PUD_UP)

        GPIO.add_event_detect(self.pin_start, GPIO.FALLING, callback=self.start_capture_gpio, bouncetime=300)
        GPIO.add_event_detect(self.pin_stop,  GPIO.BOTH, callback=self.handle_shutdown_button, bouncetime=300)

        self.root.bind("<Escape>", self.toggle_fullscreen)

    # Show flashing green border to indicate capture
    def show_green_border(self):
        if self.green_frames:
            return
        self.green_frames.append(tk.Frame(self.root, bg="green", height=10))
        self.green_frames[-1].place(x=0, y=0, relwidth=1)
        self.green_frames.append(tk.Frame(self.root, bg="green", width=10))
        self.green_frames[-1].place(x=0, y=0, relheight=1)
        self.green_frames.append(tk.Frame(self.root, bg="green", width=10))
        self.green_frames[-1].place(relx=1.0, x=-10, y=0, relheight=1)
        self.green_frames.append(tk.Frame(self.root, bg="green", height=10))
        self.green_frames[-1].place(x=0, rely=1.0, y=-10, relwidth=1)
        self.blinking_active = True
        self.blink_border()

    # Hide green border
    def hide_green_border(self):
        self.blinking_active = False
        for frame in self.green_frames:
            frame.destroy()
        self.green_frames.clear()

    # Make the border blink
    def blink_border(self):
        if not self.blinking_active:
            return
        state = self.green_frames[0].cget("bg")
        new_color = "black" if state == "green" else "green"
        for frame in self.green_frames:
            frame.configure(bg=new_color)
        self.root.after(500, self.blink_border)

    # Handle shutdown GPIO logic
    def handle_shutdown_button(self, channel):
        if GPIO.input(self.pin_stop) == GPIO.LOW:
            self.hold_start_time = time.time()
            self.shutdown_msg_timer = self.root.after(2000, self.show_shutdown_message)
            self.shutdown_timer = self.root.after(self.shutdown_hold_time, self.shutdown_system)
        else:
            if self.shutdown_timer:
                self.root.after_cancel(self.shutdown_timer)
                self.shutdown_timer = None
            if self.shutdown_msg_timer:
                self.root.after_cancel(self.shutdown_msg_timer)
                self.shutdown_msg_timer = None
            self.hide_shutdown_popup()
            duration = time.time() - getattr(self, 'hold_start_time', 0)
            if duration < self.shutdown_hold_time / 1000:
                self.stop_capture()

    # Show full-screen shutdown popup
    def show_shutdown_message(self):
        if self.shutdown_popup or self.animation_active:
            return
        self.shutdown_popup = Toplevel(self.root)
        self.shutdown_popup.attributes('-fullscreen', True)
        self.shutdown_popup.configure(bg='black')
        label = tk.Label(self.shutdown_popup, text="Shutting down...", fg='white', bg='black', font=('Helvetica', 32, 'bold'))
        label.pack(expand=True)
        self.animation_active = True

    def hide_shutdown_popup(self):
        if self.shutdown_popup:
            self.shutdown_popup.destroy()
            self.shutdown_popup = None
            self.animation_active = False

    def shutdown_system(self):
        self.show_shutdown_message()
        self.root.after(3000, lambda: os.system("sudo shutdown now"))

    # Start capture via GPIO
    def start_capture_gpio(self, channel):
        self.start_capture()

    # Create pop-up console for output
    def create_console_window(self):
        if self.console_window is not None:
            return
        self.console_window = Toplevel(self.root)
        self.console_window.title("Console Output")
        self.console_window.configure(bg="black")
        self.console_window.attributes("-topmost", True)
        w, h = 500, 150
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = int((sw - w) / 2)
        y = int((sh - h) / 2)
        self.console_window.geometry(f"{w}x{h}+{x}+{y}")
        self.console_text = tk.Text(self.console_window, height=5, width=25, font=("Helvetica", 10), bg="black", fg="white")
        self.console_text.pack(expand=True, fill='both')
        self.console_window.protocol("WM_DELETE_WINDOW", self.hide_console)

    def write(self, text):
        self.create_console_window()
        if self.hide_timer:
            self.console_window.after_cancel(self.hide_timer)
        self.console_text.insert(tk.END, text)
        self.console_text.see(tk.END)
        self.console_text.update()
        self.hide_timer = self.console_window.after(AUTOHIDE_DELAY_MS, self.hide_console)

    def flush(self):
        pass

    def hide_console(self):
        if self.console_window:
            self.console_window.destroy()
            self.console_window = None
            self.console_text = None
            self.hide_timer = None

    # Launch a script and optionally track it as capture
    def run_script(self, script, is_capture=False):
        try:
            if is_capture:
                self.show_green_border()
            process = subprocess.Popen(['python3', script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if is_capture:
                self.capture_process = process
            if process.stdout:
                for line in process.stdout:
                    self.write(line)
                process.stdout.close()
            process.wait()
        except Exception as e:
            self.write(f"Error running {script}: {e}\n")
        finally:
            if is_capture:
                self.capture_process = None
                self.hide_green_border()

    # Button: detect devices
    def detect_devices(self):
        threading.Thread(target=self.run_script, args=('Detect_Devices.py',), kwargs={'is_capture': False}, daemon=True).start()

    # Button: open configuration
    def open_config(self):
        threading.Thread(target=self.run_script, args=('configurar_parametros.py',), kwargs={'is_capture': False}, daemon=True).start()

    # Button: start capture
    def start_capture(self):
        if self.capture_process is not None:
            messagebox.showinfo("Info", "Capture already in progress.")
            return
        threading.Thread(target=self.run_script, args=('capturar_imagenes_gps.py',), kwargs={'is_capture': True}, daemon=True).start()

    # Button: open live view
    def capture_and_preview(self):
        threading.Thread(target=self.run_script, args=('Focus_test.py',), kwargs={'is_capture': False}, daemon=True).start()

    # Button: stop capture
    def stop_capture(self):
        if self.capture_process is not None and self.capture_process.poll() is None:
            confirm = messagebox.askyesno("Confirm", "Are you sure you want to stop the capture?")
            if not confirm:
                return
            self.capture_process.send_signal(signal.SIGINT)
            try:
                self.capture_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.write("The process did not close in time. It will be forced to stop.\n")
                self.capture_process.kill()
            self.capture_process = None
            self.hide_green_border()
        else:
            messagebox.showinfo("Info", "There's no active capture.")

    # Button: open additional tools
    def open_tools(self):
        try:
            subprocess.Popen(['python3', 'Herramientas.py'])
        except Exception as e:
            self.write(f"Cannot open tools: {e}\n")

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', self.is_fullscreen)
        return "break"

# Initialize the main interface
root = tk.Tk()
app = InterfaceApp(root)
root.mainloop()
GPIO.cleanup()
