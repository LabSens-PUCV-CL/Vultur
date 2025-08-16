#!/usr/bin/env python3
# vultur_rx2.py – PLC GUI + ACK  |  Quinta Región map
# Control Panel ancho, LED centrado y botones Inicio / Detener
# que ocupan TODO el ancho (Inicio verde, Stop rojo).
# ASCII-only  ·  Python ≥3.9

# ─────────────────────────────────────  IMPORTS  ────────────────────────────
import sys, io, math, threading, time, queue, re
import tkinter as tk
from tkinter import ttk, scrolledtext
from PIL import Image, ImageTk
from pymavlink import mavutil
from shapely.geometry import box
import geopandas as gpd, contextily as ctx
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ─────────────────────────────────── CONFIG GLOBAL ──────────────────────────
SERIAL_PORT = "COM5"   # ← ajusta
BAUD_RATE   = 57600

REGION_WGS  = (-72.5, -34.1, -70.3, -32.7)   # Quinta Región (lon/lat bbox)
FOV_H_DEG, FOV_V_DEG = 35.5, 20.4
MIN_SIDE_M  = 707.0
EARTH_R     = 6378137.0
PLACE_W, PLACE_H = 640, 360                   # placeholder gris

# ───────────────────────────── ESTADO COMPARTIDO ────────────────────────────
rects, rect_lock = [], threading.Lock()
img_q1, img_q2   = queue.Queue(), queue.Queue()
data_queue       = queue.Queue()
photo_idx        = 0
mav_conn         = None

# ───────────────────────────── FUNCIONES AUXILIARES ─────────────────────────
def m2ll(lat, lon, dx, dy):
    dlat = dy / EARTH_R * 180 / math.pi
    dlon = dx / (EARTH_R * math.cos(math.radians(lat))) * 180 / math.pi
    return lat + dlat, lon + dlon

def ground_rect(lat, lon, alt):
    alt = max(alt, 50)
    w = 2*alt*math.tan(math.radians(FOV_H_DEG/2))
    h = 2*alt*math.tan(math.radians(FOV_V_DEG/2))
    lat1, lon1 = m2ll(lat, lon, -w/2, -h/2)
    lat2, lon2 = m2ll(lat, lon,  w/2,  h/2)
    return box(min(lon1,lon2), min(lat1,lat2), max(lon1,lon2), max(lat1,lat2))

class RedirectStd:
    def __init__(self, widget): self.w, self.orig = widget, sys.__stdout__
    def write(self, msg):
        if msg:
            self.w.after(0, lambda m=msg: (
                self.w.config(state=tk.NORMAL),
                self.w.insert(tk.END, m),
                self.w.see(tk.END),
                self.w.config(state=tk.DISABLED)))
        self.orig.write(msg); self.orig.flush()
    def flush(self): pass

# ───────────────────────────── HILO MAVLINK ─────────────────────────────────
def mav_thread():
    global photo_idx, mav_conn
    try:
        mav = mavutil.mavlink_connection(SERIAL_PORT, baud=BAUD_RATE)
        mav.wait_heartbeat(timeout=10)
        print("[INIT] Heartbeat OK")
    except Exception as e:
        print("[ERR] MAV:", e); return
    mav_conn = mav

    exp_pkts, chunks, receiving = 0, {}, False
    while True:
        msg = mav.recv_match(blocking=True, timeout=5)
        if not msg: continue
        t = msg.get_type()

        if t == "STATUSTEXT" and msg.severity <= 6:
            data_queue.put(msg.text.strip())
            low = msg.text.lower()
            if low.startswith("gps ok") and "|" in msg.text:
                try:
                    lat, lon, alt = map(float, msg.text.split("|")[1].split(","))
                    with rect_lock:
                        rects.append(ground_rect(lat, lon, alt))
                        rects[:] = rects[-250:]
                except: pass

        elif t == "DATA_TRANSMISSION_HANDSHAKE" and msg.packets > 0:
            exp_pkts, chunks, receiving = msg.packets, {}, True
            print(f"[PHOTO] start – {exp_pkts} packets")

        elif t == "ENCAPSULATED_DATA" and receiving:
            chunks[msg.seqnr] = bytes(msg.data)
            if len(chunks) == exp_pkts:
                receiving = False
                buf = io.BytesIO(b"".join(chunks[i] for i in range(exp_pkts)))
                try:
                    pil = Image.open(buf)
                    (img_q1 if photo_idx == 0 else img_q2).put(pil)
                    photo_idx ^= 1
                    print("[PHOTO] decoded")
                except Exception as e:
                    print("[ERR] decode:", e)

# ───────────────────────────── GUI PRINCIPAL ────────────────────────────────
class VulturGUI:
    def __init__(self, root):
        self.root = root
        root.title("Vultur Monitor — Quinta Región")

        # Layout: columna 0 doble ancho
        root.columnconfigure(0, weight=0, minsize=260)
        root.columnconfigure(1, weight=1)
        root.columnconfigure(2, weight=0, minsize=PLACE_W+30)
        root.rowconfigure(0, weight=1)
        root.rowconfigure(1, weight=0)

        # ========= CONTROL PANEL =========
        cp = ttk.LabelFrame(root, text="Control Panel")
        cp.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        led_frame = ttk.Frame(cp)
        led_frame.pack(fill="x", pady=6)
        ttk.Label(led_frame, text="Estado captura",
                  font=("Segoe UI", 14, "bold")).pack()
        self.led = tk.Canvas(led_frame, width=32, height=32,
                             highlightthickness=0)
        self.led.create_oval(2,2,30,30, fill="red", tags="lamp")
        self.led.pack(pady=4)

        ttk.Label(cp, text="Últimas coord.",
                  font=("Segoe UI",13,"bold")).pack(anchor="w", padx=12)
        self.coord = tk.StringVar(value="---")
        ttk.Label(cp, textvariable=self.coord,
                  font=("Consolas",13)).pack(anchor="w", padx=12, pady=(0,12))

        ttk.Label(cp, text="Fotos tomadas",
                  font=("Segoe UI",13,"bold")).pack(anchor="w", padx=12)
        self.counter = tk.StringVar(value="0")
        ttk.Entry(cp, textvariable=self.counter, font=("Consolas",16),
                  state="readonly", width=14, justify="right").pack(anchor="w", padx=12, pady=(0,18))

        # # ----- Botones ocupa-ancho -----
        tk.Button(cp, text="Iniciar captura", fg="white", bg="#2ecc71",
                  activebackground="#27ae60", font=("Segoe UI",12,"bold"),
                  command=self.start_capture).pack(fill="x", padx=12, pady=(0,8))

        tk.Button(cp, text="Detener captura", fg="white", bg="#e74c3c",
                  activebackground="#c0392b", font=("Segoe UI",12,"bold"),
                  command=self.stop_capture).pack(fill="x", padx=12, pady=(0,8))

        tk.Button(cp, text="Snapshot 2 fotos", fg="white", bg="#3498db",
                  activebackground="#2980b9", font=("Segoe UI",12,"bold"),
                  command=self.snapshot_pair).pack(fill="x", padx=12, pady=(0,6))

        # ========= MAPA =========
        mp = ttk.LabelFrame(root, text="Map")
        mp.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        self.fig = Figure(figsize=(5,4)); self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=mp)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # ========= IMÁGENES =========
        im = ttk.LabelFrame(root, text="Images")
        im.grid(row=0, column=2, sticky="nsew", padx=6, pady=6)
        im.rowconfigure((0,2), weight=0); im.rowconfigure((1,3), weight=1)
        im.columnconfigure(0, weight=1)
        ph = ImageTk.PhotoImage(Image.new("RGB",(PLACE_W,PLACE_H),"#444"))
        self.photo1 = self.photo2 = ph
        ttk.Label(im, text="CAM 1").grid(row=0, column=0, pady=(2,0))
        self.lbl1 = ttk.Label(im, image=ph, relief="sunken")
        self.lbl1.grid(row=1, column=0, sticky="nsew", padx=2, pady=(0,6))
        ttk.Label(im, text="CAM 2").grid(row=2, column=0, pady=(2,0))
        self.lbl2 = ttk.Label(im, image=ph, relief="sunken")
        self.lbl2.grid(row=3, column=0, sticky="nsew", padx=2, pady=(0,2))

        # ========= CONSOLA =========
        cf = ttk.LabelFrame(root, text="Console")
        cf.grid(row=1,column=0,columnspan=3,sticky="nsew", padx=6, pady=6)
        console = scrolledtext.ScrolledText(cf, font=("Consolas",10),
                                            height=6, state=tk.DISABLED)
        console.pack(fill="both", expand=True, padx=2, pady=2)
        sys.stdout = sys.stderr = RedirectStd(console)

        # Timers
        root.after(200, self.pull_cam1)
        root.after(200, self.pull_cam2)
        root.after(300, self.pull_status)
        root.after(2000, self.update_map)


    # ---------- Botones lógicos ----------
    def start_capture(self):
        print("[GUI] Start capture clicked")
        if mav_conn:
            mav_conn.mav.statustext_send(6, b"START")

    def stop_capture(self):
        print("[GUI] Stop capture clicked")
        if mav_conn:
            mav_conn.mav.statustext_send(6, b"STOP")

    def snapshot_pair(self):
        print("[GUI] Snapshot button clicked")
        if mav_conn:
            mav_conn.mav.statustext_send(6, b"CMD_SNAPSHOT")

    def _led(self, color): self.led.itemconfigure("lamp", fill=color)

    # ----- Imágenes -----
    def pull_cam1(self):
        try:
            while True: self._show("cam1", img_q1.get_nowait())
        except queue.Empty: pass
        self.root.after(200, self.pull_cam1)
    def pull_cam2(self):
        try:
            while True: self._show("cam2", img_q2.get_nowait())
        except queue.Empty: pass
        self.root.after(200, self.pull_cam2)

    def _show(self, tag, pil):
        tkimg = ImageTk.PhotoImage(pil)
        if tag == "cam1":
            self.photo1 = tkimg; self.lbl1.configure(image=tkimg)
        else:
            self.photo2 = tkimg; self.lbl2.configure(image=tkimg)
        if mav_conn:
            mav_conn.mav.statustext_send(6, f"Photo {tag} ok".encode()[:50])

    # ----- Status -----
    def pull_status(self):
        try:
            while True:
                txt = data_queue.get_nowait(); low = txt.lower()
                if "captura iniciada" in low: self._led("red"); self.counter.set("0")
                elif "captura activa" in low: self._led("green")
                elif "captura detenida" in low: self._led("red")
                m = re.search(r"\((\d+)\s*fot", low)
                if m: self.counter.set(m.group(1))
                if low.startswith("gps ok") and "|" in txt:
                    try:
                        lat, lon, alt = map(float, txt.split("|")[1].split(","))
                        self.coord.set(f"{lat:.5f}, {lon:.5f}, {alt:.0f} m")
                    except: pass
        except queue.Empty: pass
        self.root.after(300, self.pull_status)

    # ----- Map -----
    def update_map(self):
        self.ax.clear()
        with rect_lock:
            drew = bool(rects)
            if drew:
                gdf = gpd.GeoDataFrame(geometry=rects, crs="EPSG:4326").to_crs(epsg=3857)
                gdf.plot(ax=self.ax, edgecolor="lime", facecolor="none", linewidth=2)
                x0,y0,x1,y1 = gdf.total_bounds
                pad_x = max(0, MIN_SIDE_M-(x1-x0))/2
                pad_y = max(0, MIN_SIDE_M-(y1-y0))/2
                self.ax.set_xlim(x0-pad_x, x1+pad_x); self.ax.set_ylim(y0-pad_y, y1+pad_y)
                try: ctx.add_basemap(self.ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=17)
                except Exception as e: print("[WARN] basemap:", e)
            else:
                lon0, lat0, lon1, lat1 = REGION_WGS
                poly = gpd.GeoSeries([box(lon0, lat0, lon1, lat1)],
                                     crs="EPSG:4326").to_crs(epsg=3857)
                poly.boundary.plot(ax=self.ax, edgecolor="orange", linewidth=1.5)
                bounds = poly.total_bounds
                self.ax.set_xlim(bounds[0], bounds[2]); self.ax.set_ylim(bounds[1], bounds[3])
                try: ctx.add_basemap(self.ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=9)
                except Exception as e: print("[WARN] basemap:", e)

        self.ax.set_title("Coverage")
        self.canvas.draw_idle()
        self.root.after(2000, self.update_map)

# ──────────────────────────────── MAIN ─────────────────────────────────────
def main():
    root = tk.Tk()
    VulturGUI(root)
    threading.Thread(target=mav_thread, daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    main()
