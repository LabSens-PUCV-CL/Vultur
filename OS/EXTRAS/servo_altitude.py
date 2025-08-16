
import tkinter as tk
import RPi.GPIO as GPIO
import time

# Configuración de servo
SERVO_GPIO = 5
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_GPIO, GPIO.OUT)
servo = GPIO.PWM(SERVO_GPIO, 50)
servo.start(0)

def mover_servo(angle):
    angle = max(0, min(180, angle))
    duty = 2.5 + (angle / 18)
    servo.ChangeDutyCycle(duty)
    time.sleep(0.3)
    servo.ChangeDutyCycle(0)
    label_status.config(text=f"Servo ajustado a {angle}°")

# Alturas y ángulos arbitrarios
alturas = {
    "50 m": 30,
    "80 m": 20,
    "120 m": 10,
    "150 m": 5
}

def seleccionar_altura(altura):
    angulo = alturas[altura]
    mover_servo(angulo)

def salir():
    try:
        servo.stop()
        GPIO.cleanup()
    except:
        pass
    app.destroy()

# Interfaz
app = tk.Tk()
app.title("Selector de Altura y Enfoque")
app.configure(bg='black')
app.attributes('-fullscreen', True)

label_titulo = tk.Label(app, text="Flight height", font=("Helvetica", 20), fg="cyan", bg="black")
label_titulo.pack(pady=25)

frame = tk.Frame(app, bg='black')
frame.pack()

# Crear botones en 2x2
labels = list(alturas.keys())
for i in range(2):
    for j in range(2):
        idx = i * 2 + j
        label = labels[idx]
        btn = tk.Button(frame, text=label, font=("Helvetica", 18), width=10, height=2,
                        bg="gray25", fg="white", activebackground="gray40",
                        command=lambda l=label: seleccionar_altura(l))
        btn.grid(row=i, column=j, padx=20, pady=15)

label_status = tk.Label(app, text="", font=("Helvetica", 16), fg="lime", bg="black")
label_status.pack(pady=10)

btn_x = tk.Button(app, text="x", command=salir,
                  font=("Helvetica", 18), width=2, height=1,
                  bg="red", fg="white")
btn_x.place(relx=0.97, rely=0.02, anchor="ne")

app.mainloop()
