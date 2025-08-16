import pandas as pd
import folium
import base64
import os
import tifffile
import numpy as np
from PIL import Image
from io import BytesIO
import tkinter as tk
from tkinter import filedialog

# Selección de carpeta
tk.Tk().withdraw()
carpeta = filedialog.askdirectory(title="Selecciona la carpeta de la campaña")

if not carpeta:
    print("❌ No se seleccionó ninguna carpeta.")
    exit()

print(f"📁 Carpeta seleccionada: {carpeta}")

# Cargar CSV
csv_path = os.path.join(carpeta, "log_Campaña.csv")
df = pd.read_csv(csv_path, encoding='latin1')
df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')

mask = (df['Lat'] < -70) & (df['Lon'] > -40)
df.loc[mask, ['Lat', 'Lon']] = df.loc[mask, ['Lon', 'Lat']].values

df_validas = df[(df['Lat'] < 0) & (df['Lat'] > -90) & (df['Lon'] < 0) & (df['Lon'] > -75)]

cam1_dir = os.path.join(carpeta, "CAM1")
cam2_dir = os.path.join(carpeta, "CAM2")
preview1_dir = os.path.join(carpeta, "CAM1_preview")
preview2_dir = os.path.join(carpeta, "CAM2_preview")

os.makedirs(preview1_dir, exist_ok=True)
os.makedirs(preview2_dir, exist_ok=True)

def generar_jpg_si_no_existe(tiff_path, jpg_path):
    if os.path.exists(jpg_path):
        return
    if not os.path.exists(tiff_path):
        return
    try:
        print(f"🔄 Generando preview: {jpg_path}")
        img_array = tifffile.imread(tiff_path)
        img_8bit = (img_array / 16).clip(0, 255).astype(np.uint8)
        img_pil = Image.fromarray(img_8bit)
        img_pil.thumbnail((800, 800))
        img_pil.save(jpg_path, format="JPEG", quality=70)
    except Exception as e:
        print(f"⚠️ Error al convertir {tiff_path} → {e}")

def codificar_jpg(path, max_ancho=640):
    if not os.path.exists(path):
        return f"<i>Archivo no encontrado:<br>{path}</i>"
    try:
        img = Image.open(path)
        img.thumbnail((max_ancho, max_ancho * img.height // img.width))
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=70)
        encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'<img src="data:image/jpeg;base64,{encoded}" width="{img.width}">'
    except Exception as e:
        return f"<i>Error al procesar imagen:<br>{e}</i>"

# Convertir imágenes
for _, row in df.iterrows():
    tiff1 = os.path.join(cam1_dir, row["Img_cam1"])
    tiff2 = os.path.join(cam2_dir, row["Img_cam2"])
    jpg1 = os.path.join(preview1_dir, row["Img_cam1"].replace(".tiff", ".jpg"))
    jpg2 = os.path.join(preview2_dir, row["Img_cam2"].replace(".tiff", ".jpg"))
    generar_jpg_si_no_existe(tiff1, jpg1)
    generar_jpg_si_no_existe(tiff2, jpg2)

# Crear mapa solo si hay coordenadas válidas
if not df_validas.empty:
    m = folium.Map(
        location=[df_validas['Lat'].iloc[0], df_validas['Lon'].iloc[0]],
        zoom_start=18,
        max_zoom=22,
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri — World Imagery'
    )

    for _, row in df_validas.iterrows():
        jpg1 = os.path.join(preview1_dir, row["Img_cam1"].replace(".tiff", ".jpg"))
        jpg2 = os.path.join(preview2_dir, row["Img_cam2"].replace(".tiff", ".jpg"))

        popup_html = (
            f"<b>CAM1:</b><br>{codificar_jpg(jpg1)}<br><br>"
            f"<b>CAM2:</b><br>{codificar_jpg(jpg2)}"
        )

        folium.Marker(
            location=[row['Lat'], row['Lon']],
            popup=folium.Popup(popup_html, max_width=700),
            tooltip=row["Img_cam1"]
        ).add_to(m)

    output_path = os.path.join(carpeta, "mapa_interactivo.html")
    m.save(output_path)
    print(f"✅ Mapa generado: {output_path}")
else:
    print("⚠️ No se encontraron coordenadas válidas. Solo se generaron los JPG.")
