#!/usr/bin/env python3
# enviar_2fotos.py  –  simultaneous capture, waits for ACK from PC   ASCII-only

import io, time, json, sys, re
from pathlib import Path
from pypylon import pylon, genicam
from PIL import Image
from pymavlink import mavutil

# ---- CONFIG ------------------------------------------------------------
SERIAL_PORT  = "/dev/serial0"
BAUD_RATE    = 57600
PAYLOAD      = 253
JPEG_Q       = 30
ACK_TIMEOUT  = 20           # seconds to wait for "Photo camX ok"
MAX_RETRIES = 3  

PRM      = json.load(open("config.json"))["Camaras"]
WIDTH    = 3840
HEIGHT   = 2160
EXPOSURE = int(PRM.get("ExposureTime", 500))
GAIN     = float(PRM.get("Gain", 0))
RESIZE_W = int(PRM.get("Resize", 640))
# ------------------------------------------------------------------------

def log(msg): print(time.strftime("[%H:%M:%S]"), msg, flush=True)

def capture_both(cams):
    for cam in cams:
        cam.Open()
        cam.Width.Value = WIDTH; cam.Height.Value = HEIGHT
        cam.PixelFormat.Value = "Mono12"
        cam.ExposureTime.Value = EXPOSURE; cam.Gain.Value = GAIN
        cam.TriggerSelector.Value = "FrameStart"
        cam.TriggerMode.Value = "On"; cam.TriggerSource.Value = "Software"
        cam.AcquisitionMode.SetValue("Continuous")
        cam.StartGrabbing()

    for cam in cams:
        try: cam.TriggerSoftware.Execute()
        except genicam.GenericException: cam.ExecuteSoftwareTrigger()

    out = {}
    for idx, cam in enumerate(cams):
        res = cam.RetrieveResult(3000); arr = res.Array; res.Release()
        cam.StopGrabbing(); cam.Close()
        pil = Image.fromarray((arr/16).astype("uint8"))
        if RESIZE_W and RESIZE_W < pil.width:
            pil = pil.resize((RESIZE_W, int(pil.height*RESIZE_W/pil.width)))
        buf = io.BytesIO(); pil.save(buf,"JPEG",quality=JPEG_Q)
        out[f"cam{idx+1}"] = (buf.getvalue(), pil.width, pil.height)
        buf.close()
        log(f"cam{idx+1}: captured & {len(out[f'cam{idx+1}'][0])} B")
    return out

def send_photo(mav, data, w, h, tag):
    for attempt in range(1, MAX_RETRIES + 1):            # ← bucle reintento
        log(f"{tag}: attempt {attempt}/{MAX_RETRIES}")

        pkts = (len(data)+PAYLOAD-1)//PAYLOAD
        pause = max(0.02, 0.007*pkts)

        # handshake START
        mav.mav.data_transmission_handshake_send(
            mavutil.mavlink.MAVLINK_DATA_STREAM_IMG_JPEG,
            len(data), w, h, pkts, PAYLOAD, JPEG_Q)
        time.sleep(0.25)

        # data packets
        for seq in range(pkts):
            chunk = data[seq*PAYLOAD:(seq+1)*PAYLOAD].ljust(PAYLOAD,b'\0')
            mav.mav.encapsulated_data_send(seq, chunk)
            time.sleep(pause)

        # handshake END
        mav.mav.data_transmission_handshake_send(
            mavutil.mavlink.MAVLINK_DATA_STREAM_IMG_JPEG, 0,0,0,0,0,0)

        deadline = time.time() + ACK_TIMEOUT
        got_ack  = False

        while time.time() < deadline:
            m = mav.recv_match(type="STATUSTEXT", blocking=True, timeout=2)
            if not m:
                continue
            txt = m.text.strip().lower()

            if txt.startswith("retry:"):
                miss=list(map(int,re.findall(r"\d+",txt)))
                log(f"{tag}: resend {miss}")
                for seq in miss:
                    ch=data[seq*PAYLOAD:(seq+1)*PAYLOAD].ljust(PAYLOAD,b'\0')
                    mav.mav.encapsulated_data_send(seq,ch)
                    time.sleep(pause)

            elif f"photo {tag} ok" in txt:
                got_ack = True
                break                                   # ← ACK recibido

        if got_ack:
            mav.mav.statustext_send(6, f"Photo {tag} sent".encode("ascii")[:50])
            log(f"{tag}: ACK received, done")
            return                                      # exit after success

        log(f"{tag}: ACK timeout ({ACK_TIMEOUT}s) – retrying …")

    # se agotaron los intentos
    log(f"{tag}: FAILED after {MAX_RETRIES} attempts")

def main():
    mav = mavutil.mavlink_connection(SERIAL_PORT, baud=BAUD_RATE)
    mav.wait_heartbeat(timeout=10); log("Heartbeat OK – capturing…")

    factory = pylon.TlFactory.GetInstance()
    devs = factory.EnumerateDevices()
    if len(devs) < 2: sys.exit("Need at least 2 Basler cameras")

    cams = [pylon.InstantCamera(factory.CreateDevice(devs[i])) for i in (0,1)]
    imgs = capture_both(cams)           # simultaneous shoot

    for tag in ("cam1","cam2"):
        data,w,h = imgs[tag]
        send_photo(mav,data,w,h,tag); time.sleep(0.2)

    log("Done")

if __name__=="__main__": main()
