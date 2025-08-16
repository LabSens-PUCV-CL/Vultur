"""
This script captures synchronized images from two cameras using a master-slave trigger scheme.
It records GPS and attitude data from a MAVLink connection, saves the images as TIFF files,
and logs metadata to a CSV file. It also uses GPIO LEDs to indicate system status.

"""

from pypylon import pylon
import tifffile as tiff
import json, time, datetime, csv, pathlib, sys, signal, threading
import RPi.GPIO as GPIO
from pymavlink import mavutil

# ───────── GPIO Setup ─────────
LED_RUN, LED_WARN = 16, 20          # GPIO pins for RUN and WARNING LEDs
stop = False                        # Global flag for graceful shutdown
print_fix_warning = True           # Show GPS warning only once

# ───────── State Variables ─────────
photo_counter = 0
last_send_time = time.time()
status_path = None  # Reserved for future use

# ───────── MAVLink Messaging ─────────
def send_mavlink_message(text):
    def worker():
        try:
            mav.mav.statustext_send(severity=6, text=text.encode("utf-8")[:50])
        except Exception as e:
            print("MAVLink TX Error:", e)
    threading.Thread(target=worker, daemon=True).start()

# ───────── Signal Handlers ─────────
def _stop(*_):
    global stop
    stop = True

signal.signal(signal.SIGINT , _stop)
signal.signal(signal.SIGTERM, _stop)

# ───────── GPIO Initialization ─────────
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_RUN , GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(LED_WARN, GPIO.OUT, initial=GPIO.LOW)

# ───────── Load Camera Configuration ─────────
params = json.load(open("config.json"))["Cameras"]
FPS  = float(params.get("FPS", 2))
EXP  = int(params.get("ExposureTime", 500))
GAIN = float(params.get("Gain", 0))
PERIOD = 1 / FPS
DELAY = 0.01  # Delay between master and slave trigger

# ───────── GPS / Attitude State ─────────
gps_ok = False
last_gps = {"time": None, "lat": None, "lon": None, "alt": None}
last_att = {"yaw": None, "pitch": None, "roll": None, "gs": None, "climb": None}

# ───────── MAVLink Listener Thread ─────────
def gps_reader():
    global gps_ok, print_fix_warning
    while True:
        try:
            msg = mav.recv_match(type=['GLOBAL_POSITION_INT','GPS_RAW_INT','ATTITUDE','VFR_HUD'],
                                 blocking=True, timeout=1)
        except Exception:
            continue
        if not msg:
            continue

        if msg.get_type() == "GLOBAL_POSITION_INT" and msg.lat not in (0, 0x7FFFFFFF):
            gps_ok = True
            last_gps.update(
                time=datetime.datetime.utcnow().isoformat(timespec="milliseconds"),
                lat=msg.lat/1e7, lon=msg.lon/1e7, alt=msg.alt/1000.0)

        elif msg.get_type() == "GPS_RAW_INT":
            if msg.fix_type >= 3 and msg.lat not in (0, 0x7FFFFFFF):
                gps_ok = True
                last_gps.update(
                    time=datetime.datetime.utcnow().isoformat(timespec="milliseconds"),
                    lat=msg.lat/1e7, lon=msg.lon/1e7, alt=msg.alt/1000.0)
            elif print_fix_warning:
                print_fix_warning = False

        elif msg.get_type() == "ATTITUDE":
            last_att.update(
                yaw=round(msg.yaw * 57.2958, 2),
                pitch=round(msg.pitch * 57.2958, 2),
                roll=round(msg.roll * 57.2958, 2))

        elif msg.get_type() == "VFR_HUD":
            last_att.update(gs=msg.groundspeed, climb=msg.climb)

# ───────── Initialize MAVLink ─────────
try:
    mav = mavutil.mavlink_connection('/dev/serial0', baud=57600)
    mav.wait_heartbeat(timeout=3)
    threading.Thread(target=gps_reader, daemon=True).start()
except Exception:
    gps_ok = False

# ───────── Blink Warning LED if GPS is not OK ─────────
if not gps_ok:
    for _ in range(2):
        GPIO.output(LED_WARN, 1); time.sleep(0.25)
        GPIO.output(LED_WARN, 0); time.sleep(0.25)

# ───────── Create Output Folders ─────────
now = datetime.datetime.now()
root = pathlib.Path.home() / f"Campaign {now:%d-%m-%Y} - {now:%Hh%Mm%Ss}"
(cam1_dir := root / "CAM1").mkdir(parents=True, exist_ok=True)
(cam2_dir := root / "CAM2").mkdir(exist_ok=True)
csv_path = root / "Campaign_log.csv"

# ───────── Save Parameters to JSON ─────────
metadata = {
    "Start_time": now.isoformat(sep=" ", timespec="seconds"),
    "FPS": FPS,
    "Master_slave_delay_s": DELAY,
    "ExposureTime_us": EXP,
    "Gain": GAIN,
    "PixelFormat": "Mono12",
    "GPS_detected": gps_ok
}
json.dump(metadata, open(root / "Parameters.json", "w"), indent=2)

# ───────── Camera Setup ─────────
tl = pylon.TlFactory.GetInstance()
devices = tl.EnumerateDevices()
if len(devices) < 2:
    GPIO.cleanup()
    sys.exit("Connect 2 cameras")

cam1, cam2 = [pylon.InstantCamera(tl.CreateDevice(d)) for d in devices[:2]]

def configure_camera(cam):
    cam.Open()
    cam.Width.Value = 3840
    cam.Height.Value = 2160
    cam.PixelFormat.Value = "Mono12"
    cam.ExposureTime.Value = EXP
    cam.Gain.Value = GAIN
    cam.TriggerSelector.Value = "FrameStart"
    cam.TriggerMode.Value = "On"
    cam.TriggerSource.Value = "Software"

for cam in (cam1, cam2):
    configure_camera(cam)
    cam.StartGrabbing(pylon.GrabStrategy_OneByOne)

# ───────── Start Capture ─────────
GPIO.output(LED_RUN, 1)
send_mavlink_message("Capture started")

# ───────── Main Capture Loop ─────────
with csv_path.open("w", newline="") as fcsv:
    writer = csv.writer(fcsv)
    writer.writerow(["RTC_time", "GPS_time", "cam1_img", "cam2_img",
                     "Latitude", "Longitude", "Altitude",
                     "Yaw_deg", "Pitch_deg", "Roll_deg", "GroundSpeed", "Climb"])

    try:
        while not stop:
            start_time = time.time()

            # Trigger both cameras
            cam1.ExecuteSoftwareTrigger()
            r1 = cam1.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            time.sleep(DELAY)
            cam2.ExecuteSoftwareTrigger()
            r2 = cam2.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

            if r1.GrabSucceeded() and r2.GrabSucceeded():
                # Get time and metadata
                rtc = datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")
                gps_time = last_gps["time"] or "NONE"
                lat = last_gps["lat"] if last_gps["lat"] is not None else "NONE"
                lon = last_gps["lon"] if last_gps["lon"] is not None else "NONE"
                alt = last_gps["alt"] if last_gps["alt"] is not None else "NONE"

                yaw   = last_att["yaw"]   if last_att["yaw"] is not None else "NONE"
                pitch = last_att["pitch"] if last_att["pitch"] is not None else "NONE"
                roll  = last_att["roll"]  if last_att["roll"] is not None else "NONE"
                gs    = last_att["gs"]    if last_att["gs"] is not None else "NONE"
                climb = last_att["climb"] if last_att["climb"] is not None else "NONE"

                timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                f1 = cam1_dir / f"cam1_{timestamp}.tiff"
                f2 = cam2_dir / f"cam2_{timestamp}.tiff"

                tiff.imwrite(f1, r1.GetArray(), photometric="minisblack")
                tiff.imwrite(f2, r2.GetArray(), photometric="minisblack")

                writer.writerow([rtc, gps_time, f1.name, f2.name,
                                 lat, lon, alt, yaw, pitch, roll, gs, climb])
                fcsv.flush()
                photo_counter += 1

                send_mavlink_message(f"GPS OK | {lat},{lon},{alt}")
                send_mavlink_message(f"Active capture ({photo_counter} photos)")

            r1.Release()
            r2.Release()
            time.sleep(max(0, PERIOD - (time.time() - start_time)))

    finally:
        for cam in (cam1, cam2):
            if cam.IsGrabbing():
                cam.StopGrabbing()
                cam.Close()
        GPIO.output(LED_RUN, 0)
        GPIO.cleanup()
        send_mavlink_message(f"Capture stopped ({photo_counter} photos)")
