import numpy as np
import matplotlib.pyplot as plt
import tifffile
import tkinter as tk
from tkinter import filedialog

# --- Configuración ---
tamano_ventana = 5  # Tamaño del área cuadrada para promediar (ej. 5x5)

# --- Selector de archivo ---
root = tk.Tk()
root.withdraw()
ruta_imagen = filedialog.askopenfilename(
    title="Selecciona una imagen TIFF",
    filetypes=[("TIFF files", "*.tif *.tiff")]
)

if not ruta_imagen:
    print("No se seleccionó ninguna imagen.")
    exit()

# --- Cargar imagen y normalizar a [0, 1] si es 12-bit ---
img = tifffile.imread(ruta_imagen).astype(np.float32)
if img.max() > 1.0:
    img /= 4095.0

alto, ancho = img.shape

# --- Función para mostrar el promedio ---
def mostrar_valor_promedio(event):
    if event.inaxes:
        x = int(event.xdata)
        y = int(event.ydata)

        # Calcular ventana centrada
        mitad = tamano_ventana // 2
        x1, x2 = max(0, x - mitad), min(ancho, x + mitad + 1)
        y1, y2 = max(0, y - mitad), min(alto, y + mitad + 1)

        ventana = img[y1:y2, x1:x2]
        promedio = np.mean(ventana)
        print(f"Cursor en ({x},{y}) → Promedio {tamano_ventana}x{tamano_ventana}: {promedio:.4f}")

# --- Mostrar imagen ---
fig, ax = plt.subplots()
ax.imshow(img, cmap='gray')
ax.set_title(f"{ruta_imagen} ({tamano_ventana}x{tamano_ventana})")
fig.canvas.mpl_connect('motion_notify_event', mostrar_valor_promedio)
plt.show()
