import numpy as np
import tifffile
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import tkinter as tk
from tkinter import filedialog

def cargar_y_normalizar(path):
    img = tifffile.imread(path).astype(np.float32)
    if img.max() > 1.0:
        img /= 4095.0
    return img

def seleccionar_imagen(titulo):
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(title=titulo, filetypes=[("TIFF files", "*.tif *.tiff")])

# --- Parámetros ---
tamano = 200
half = tamano // 2

# --- Selección de imágenes ---
print("Selecciona la imagen CON filtro azul:")
ruta_azul = seleccionar_imagen("Imagen con filtro azul")
print("Selecciona la imagen SIN filtro:")
ruta_total = seleccionar_imagen("Imagen sin filtro")

if not ruta_azul or not ruta_total:
    print("No se seleccionaron ambas imágenes.")
    exit()

img_azul = cargar_y_normalizar(ruta_azul)
img_total = cargar_y_normalizar(ruta_total)

h, w = img_total.shape

# --- Crear figura interactiva con 2 subplots ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
im1 = ax1.imshow(img_total, cmap="gray")
im2 = ax2.imshow(img_azul, cmap="gray")

rect1 = patches.Rectangle((0, 0), tamano, tamano, edgecolor='red', facecolor='none', linewidth=1.5)
rect2 = patches.Rectangle((0, 0), tamano, tamano, edgecolor='cyan', facecolor='none', linewidth=1.5)
ax1.add_patch(rect1)
ax2.add_patch(rect2)

info_text = fig.text(0.5, 0.95, "", ha="center", fontsize=12, backgroundcolor="black", color="white")

# Coordenadas iniciales
xy_total = [w // 2, h // 2]
xy_azul = [w // 2, h // 2]

def actualizar_ventanas():
    xt, yt = xy_total
    xa, ya = xy_azul

    xt = int(np.clip(xt, half, w - half - 1))
    yt = int(np.clip(yt, half, h - half - 1))
    xa = int(np.clip(xa, half, w - half - 1))
    ya = int(np.clip(ya, half, h - half - 1))

    zona_total = img_total[yt - half:yt + half, xt - half:xt + half]
    zona_azul = img_azul[ya - half:ya + half, xa - half:xa + half]

    prom_total = np.mean(zona_total)
    prom_azul = np.mean(zona_azul)
    porcentaje = (prom_azul / prom_total) * 100 if prom_total > 0 else 0

    rect1.set_xy((xt - half, yt - half))
    rect2.set_xy((xa - half, ya - half))

    info_text.set_text(
        f"Total({xt},{yt})  Azul({xa},{ya})  →  % Azul: {porcentaje:.2f}%"
    )
    fig.canvas.draw_idle()

def mover(event):
    if event.inaxes == ax1:
        xy_total[0], xy_total[1] = event.xdata, event.ydata
    elif event.inaxes == ax2:
        xy_azul[0], xy_azul[1] = event.xdata, event.ydata
    actualizar_ventanas()

# --- Conectar evento ---
fig.canvas.mpl_connect("motion_notify_event", mover)

ax1.set_title("Imagen SIN filtro")
ax2.set_title("Imagen CON filtro azul")
plt.tight_layout()
plt.show()
