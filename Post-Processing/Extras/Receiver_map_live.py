import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from shapely.geometry import box
import geopandas as gpd
import contextily as ctx
from pymavlink import mavutil
import threading
import math
import time

# === Parámetros de cámara ===
FOV_H = 35.5  # Horizontal FOV en grados
FOV_V = 20.4  # Vertical FOV en grados
MIN_SIDE = 707.0  # ~sqrt(500000 m²)

# === Almacenar polígonos ===
rects = []
lock = threading.Lock()

# === Conversión de metros a grados lat/lon ===
def meters_to_latlon_offset(lat, lon, dx_m, dy_m):
    R = 6378137
    dlat = (dy_m / R) * (180 / math.pi)
    dlon = (dx_m / (R * math.cos(math.radians(lat)))) * (180 / math.pi)
    return lat + dlat, lon + dlon

# === Crear rectángulo geográfico ===
def crear_rectangulo(lat, lon, alt):
    if alt < 50:
        print("Altitud menor a 50m, usando 50m como mínimo.")
        alt = 50
    w = 2 * alt * math.tan(math.radians(FOV_H / 2))
    h = 2 * alt * math.tan(math.radians(FOV_V / 2))
    lat1, lon1 = meters_to_latlon_offset(lat, lon, -w/2, -h/2)
    lat2, lon2 = meters_to_latlon_offset(lat, lon,  w/2,  h/2)
    return box(min(lon1, lon2), min(lat1, lat2), max(lon1, lon2), max(lat1, lat2))

# === Hilo de escucha MAVLink ===
def escuchar_mavlink(serial_port="COM5", baud=57600):
    try:
        print("Conectando al puerto", serial_port, "a", baud, "bps...")
        master = mavutil.mavlink_connection(serial_port, baud=baud)
        print("Esperando latido del Pixhawk o dispositivo MAVLink...")

        start_time = time.time()
        while time.time() - start_time < 15:
            try:
                hb = master.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
                if hb:
                    print("Conectado. Dispositivo MAVLink activo.\n")
                    break
            except:
                continue

        while True:
            msg = master.recv_match(type='STATUSTEXT', blocking=True, timeout=10)
            if msg and msg.severity == 6:
                texto = msg.text.strip()
                print("[Vultur RX]", texto)
                if texto.lower().startswith("gps ok") and "|" in texto:
                    try:
                        partes = texto.split("|")[1].strip().split(",")
                        lat = float(partes[0])
                        lon = float(partes[1])
                        alt = float(partes[2])
                        with lock:
                            rects.append(crear_rectangulo(lat, lon, alt))
                    except Exception as e:
                        print("Error interpretando coordenadas:", e)
    except Exception as e:
        print("Error MAVLink:", e)

# === Iniciar hilo de recepción ===
threading.Thread(target=escuchar_mavlink, daemon=True).start()

# === Mostrar y actualizar mapa ===
fig, ax = plt.subplots(figsize=(10, 8))

def actualizar(frame):
    ax.clear()
    gdf = None
    with lock:
        if rects:
            gdf = gpd.GeoDataFrame(geometry=rects, crs="EPSG:4326").to_crs(epsg=3857)
            gdf.plot(ax=ax, edgecolor='lime', facecolor='none', linewidth=2)

    if gdf is not None:
        try:
            ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, zoom=17)

            # Forzar área mínima visible
            x0, y0, x1, y1 = gdf.total_bounds
            width = x1 - x0
            height = y1 - y0

            if width < MIN_SIDE:
                extra = (MIN_SIDE - width) / 2
                x0 -= extra
                x1 += extra
            if height < MIN_SIDE:
                extra = (MIN_SIDE - height) / 2
                y0 -= extra
                y1 += extra

            ax.set_xlim(x0, x1)
            ax.set_ylim(y0, y1)

        except Exception as e:
            print("Error cargando mapa base:", e)

    ax.set_title("Cobertura Aérea - Vultur", fontsize=14)

print("Esperando datos. El mapa se actualizará automáticamente.")
ani = FuncAnimation(fig, actualizar, interval=2000)
plt.show()
