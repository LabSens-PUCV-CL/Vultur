"""
This script uses the Pypylon library to detect connected Basler cameras
on the Raspberry Pi. It provides visual feedback through a common-cathode
RGB LED connected to GPIO pins:
- Blinks red if no cameras are found.
- Blinks blue once for each detected camera.

"""

#Imports
from pypylon import pylon
import RPi.GPIO as GPIO
import time

# --- GPIO pin definitions for RGB LED (common cathode) ---
PIN_ROJO = 20
PIN_AZUL = 21

# --- GPIO setup ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_ROJO, GPIO.OUT)
GPIO.setup(PIN_AZUL, GPIO.OUT)

# --- Turn off both LED colors ---
def apagar_led_rgb():
    GPIO.output(PIN_ROJO, GPIO.LOW)
    GPIO.output(PIN_AZUL, GPIO.LOW)

# --- Turn on selected LED colors ---
def encender_color(rojo=False, azul=False):
    GPIO.output(PIN_ROJO, GPIO.HIGH if rojo else GPIO.LOW)
    GPIO.output(PIN_AZUL, GPIO.HIGH if azul else GPIO.LOW)

# --- Blink selected LED color a given number of times ---
def parpadear_color(rojo=False, azul=False, veces=3, intervalo=0.3):
    for _ in range(veces):
        encender_color(rojo=rojo, azul=azul)
        time.sleep(intervalo)
        apagar_led_rgb()
        time.sleep(intervalo)

# --- Detect connected Pypylon cameras ---
def detectar_camaras():
    try:
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()

        if len(devices) == 0:
            print("No cameras were detected")
            parpadear_color(rojo=True, veces=3)  # Red blinks = no cameras
        else:
            # Show all detected camera names
            camera_list = "\n".join([f"{i+1}. {device.GetFriendlyName()}" for i, device in enumerate(devices)])
            print(f"Detected cameras:\n{camera_list}")
            parpadear_color(azul=True, veces=len(devices))  # Blue blinks = camera count

    except Exception as e:
        print(f"There was a problem detecting cameras: {e}")
    finally:
        apagar_led_rgb()
        GPIO.cleanup()

# --- Run the detection if this script is executed directly ---
if __name__ == "__main__":
    detectar_camaras()
