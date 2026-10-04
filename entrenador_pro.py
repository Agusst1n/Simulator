import tkinter as tk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.collections import LineCollection
import random
import time
import os
from datetime import datetime, timedelta

# =====================================================================
# 📂 CONFIGURACIÓN Y LECTOR DE DATOS FINANCIEROS REALES
# =====================================================================
ARCHIVO_DATOS = "datos_broker.csv"

def inicializar_base_de_datos():
    if not os.path.exists(ARCHIVO_DATOS):
        print("[INFO] Generando base de datos limpia con hora real actual...")
        datos = []
        precio = 1.1150  # Sincronizado exactamente con tu zona actual de precios
        tiempo_base = datetime.now() - timedelta(minutes=120)
        
        for i in range(120):
            momento_vela = tiempo_base + timedelta(minutes=i)
            fecha_str = momento_vela.strftime("%Y-%m-%d")
            hora_str = momento_vela.strftime("%H:%M")
            timestamp_vela = momento_vela.timestamp()
            
            o = precio + random.uniform(-0.0001, 0.0001)
            c = o + random.uniform(-0.0001, 0.0001)
            h = max(o, c) + random.uniform(0.00005, 0.0001)
            l = min(o, c) - random.uniform(0.00005, 0.0001)
            
            ticks = [o]
            precio_actual = o
            for seg in range(1, 59):
                factor_guia = (c - precio_actual) / (60 - seg)
                ruido = random.uniform(-0.00001, 0.00001)
                precio_actual += factor_guia + ruido
                precio_actual = max(l, min(h, precio_actual))
                ticks.append(precio_actual)
            ticks.append(c)
            ticks_str = ";".join([f"{t:.5f}" for t in ticks])
            
            datos.append([fecha_str, hora_str, timestamp_vela, f"{o:.5f}", f"{h:.5f}", f"{l:.5f}", f"{c:.5f}", ticks_str])
            precio = c
        df_inicial = pd.DataFrame(datos, columns=["Fecha", "Hora", "Timestamp", "Open", "High", "Low", "Close", "Ticks_60s"])
        df_inicial.to_csv(ARCHIVO_DATOS, index=False)

inicializar_base_de_datos()
DF_MERCADO = pd.read_csv(ARCHIVO_DATOS)

# Limpiar duplicados si el grabador repitió filas por latencia de internet
DF_MERCADO = DF_MERCADO.drop_duplicates(subset=["Hora"]).reset_index(drop=True)

if len(DF_MERCADO) > 120:
    DF_MERCADO = DF_MERCADO.tail(120).reset_index(drop=True)

for col in ["Open", "High", "Low", "Close"]:
    DF_MERCADO[col] = DF_MERCADO[col].astype(float)

TOTAL_VELAS_REGISTRADAS = len(DF_MERCADO)
RANGO_ZOOM = min(45, max(5, TOTAL_VELAS_REGISTRADAS // 3))
INDICE_ACTUAL = max(RANGO_ZOOM + 1, TOTAL_VELAS_REGISTRADAS - 2)

if INDICE_ACTUAL >= TOTAL_VELAS_REGISTRADAS:
    INDICE_ACTUAL = TOTAL_VELAS_REGISTRADAS - 1

DIVISA_ACTIVA = "EURUSD-OTC"

TICKS_ACTUALES = []
ANIMANDO = False
VOTO_USUARIO = None
LINEAS_DISEÑO = [] 
MODO_DIBUJO_ACTIVO = False

TRADES_GANADOS = 0
TRADES_PERDIDOS = 0

def obtener_hora_formateada(x):
    idx = int(round(x))
    if idx < 0 or idx >= len(DF_MERCADO): return ""
    return DF_MERCADO.iloc[idx]["Hora"]

# =====================================================================
# 📉 MOTOR GRÁFICO REALISTA CORREGIDO COORDENADAS REALES
# =====================================================================
def dibujar_mercado():
    ax_velas.clear()
    ax_linea.clear()
    
    for ax in [ax_velas, ax_linea]:
        ax.set_facecolor("#0d1117")
        ax.tick_params(colors="#8b949e", labelsize=9)
        ax.grid(color="#21262d", linestyle="--", linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_color("#30363d")

    ax_velas.set_title(f"Historial {DIVISA_ACTIVA} (Velas M1)", color="white", fontsize=11, fontweight="bold")
    ax_linea.set_title("Microestructura en Directo (0-60s)", color="white", fontsize=11, fontweight="bold")
    
    # 1. Dibujar Velas Izquierdas Separadas de forma Estable
    df_previo = DF_MERCADO.iloc[:INDICE_ACTUAL]
    for i in range(len(df_previo)):
        fila = df_previo.iloc[i]
        o, h, l, c = fila["Open"], fila["High"], fila["Low"], fila["Close"]
        color = "#2ea44f" if c >= o else "#da3637"
        ax_velas.plot([i, i], [l, h], color=color, linewidth=1.2)
        ax_velas.bar(i, c - o, bottom=o, color=color, width=0.6)

    ticks_x = list(range(0, len(df_previo), max(1, len(df_previo)//5)))
    etiquetas_x = [obtener_hora_formateada(t) for t in ticks_x]
    ax_velas.set_xticks(ticks_x)
    ax_velas.set_xticklabels(etiquetas_x)
    
    for y_val in LINEAS_DISEÑO:
        ax_velas.axhline(y=y_val, color="#ff007f", linestyle="-", linewidth=1.2)
        
    idx_inicio = max(0, INDICE_ACTUAL - RANGO_ZOOM)
    ax_velas.set_xlim(idx_inicio - 0.5, INDICE_ACTUAL + 0.5)
    
    velas_visibles = df_previo.iloc[idx_inicio:INDICE_ACTUAL]
    if not velas_visibles.empty:
        ax_velas.set_ylim(velas_visibles["Low"].min() * 0.9998, velas_visibles["High"].max() * 1.0002)
    
    # 2. Configurar Gráfico de Líneas Derecho con ESCALA SINCRO REAL REALISTA
    ax_linea.set_xlim(0, 59)
    fila_v = DF_MERCADO.iloc[INDICE_ACTUAL]
    
    # FORZADO DIRECTO DE ESCALA EN BASE AL PRECIO REAL (Anula el bug de la escala 0.00022)
    margen_ini = (fila_v["High"] - fila_v["Low"]) * 0.05 if (fila_v["High"] - fila_v["Low"]) > 0 else 0.0001
    ax_linea.set_ylim(fila_v["Low"] - margen_ini, fila_v["High"] + margen_ini)
    
    h, m = map(int, fila_v["Hora"].split(":"))
    dt_objeto = datetime(2026, 10, 3, h, m)
    dt_cierre = dt_objeto + timedelta(minutes=1)
    
    ax_linea.set_xticks([0, 30, 59])
    ax_linea.set_xticklabels([dt_objeto.strftime("%H:%M:00"), dt_objeto.strftime("%H:%M:30"), dt_cierre.strftime("%H:%M:00")])
    
    actualizar_barra_superior()
    canvas.draw_idle()

def actualizar_barra_superior():
    fila_v = DF_MERCADO.iloc[INDICE_ACTUAL]
    total_trades = TRADES_GANADOS + TRADES_PERDIDOS
    win_rate = (TRADES_GANADOS / total_trades * 100) if total_trades > 0 else 0.0
    lbl_info.config(text=f"📊 DIVISA: {DIVISA_ACTIVA}  |  🕒 VELA ACTUAL: {fila_v['Hora']} M1  |  🎯 GANADAS: {TRADES_GANADOS}  ❌ PERDIDAS: {TRADES_PERDIDOS}  |  📈 WIN RATE: {win_rate:.1f}%")

def scroll_historial_nativo(val):
    global INDICE_ACTUAL
    if ANIMANDO: return
    nuevo_idx = int(float(val))
    if nuevo_idx >= RANGO_ZOOM and nuevo_idx < len(DF_MERCADO):
        INDICE_ACTUAL = nuevo_idx
        dibujar_mercado()

def zoom_rueda_mouse(event):
    global RANGO_ZOOM
    if event.inaxes != ax_velas: return
    factor = 0.8 if event.button == 'up' else 1.2
    RANGO_ZOOM = max(15, min(90, int(RANGO_ZOOM * factor)))
    slider_scroll.set(INDICE_ACTUAL)
    dibujar_mercado()

def toggle_modo_dibujo():
    global MODO_DIBUJO_ACTIVO
    MODO_DIBUJO_ACTIVO = not MODO_DIBUJO_ACTIVO
    btn_dibujo.config(bg="#ff007f" if MODO_DIBUJO_ACTIVO else "#30363d", text="✏️ DIBUJO: ACTIVO" if MODO_DIBUJO_ACTIVO else "✏️ MARCAR ZONAS")

def seleccionar_contexto_random():
    global INDICE_ACTUAL, LINEAS_DISEÑO
    if len(DF_MERCADO) > RANGO_ZOOM + 5:
        INDICE_ACTUAL = random.randint(RANGO_ZOOM + 2, len(DF_MERCADO) - 2)
        LINEAS_DISEÑO = []
        slider_scroll.set(INDICE_ACTUAL)
        dibujar_mercado()

def on_click_grafico(event):
    if event.inaxes != ax_velas or not MODO_DIBUJO_ACTIVO: return 
    if event.button == 1: 
        LINEAS_DISEÑO.append(event.ydata)
    elif event.button == 3 and LINEAS_DISEÑO:
        linea_cercana = min(LINEAS_DISEÑO, key=lambda y: abs(y - event.ydata))
        lim_inf, lim_sup = ax_velas.get_ylim()
        if abs(linea_cercana - event.ydata) < (lim_sup - lim_inf) * 0.04:
            LINEAS_DISEÑO.remove(linea_cercana)
    dibujar_mercado()

def registrar_voto(tipo):
    global VOTO_USUARIO
    VOTO_USUARIO = tipo
    btn_call.config(state="disabled")
    btn_put.config(state="disabled")
    btn_siguiente.config(state="normal", bg="#ff9900", fg="black")

def lanzar_popup_resultado(gano, o, h, l, c):
    global TRADES_GANADOS, TRADES_PERDIDOS
    if gano: TRADES_GANADOS += 1
    else: TRADES_PERDIDOS += 1
    
    popup = tk.Toplevel(root)
    popup.title("Resultado")
    popup.geometry("380x480")
    popup.configure(bg="#161b22")
    popup.resizable(False, False)
    popup.grab_set()
    
    color_t = "#2ea44f" if gano else "#da3637"
    tk.Label(popup, text="¡OPERACIÓN GANADA!" if gano else "OPERACIÓN PERDIDA", fg=color_t, bg="#161b22", font=("Arial", 16, "bold")).pack(pady=15)
    
    canvas_vela = tk.Canvas(popup, width=200, height=220, bg="#0d1117", highlightthickness=1, highlightbackground="#30363d")
    canvas_vela.pack(pady=15)
    
    color_v = "#2ea44f" if c >= o else "#da3637"
    max_rango = max(h - l, 0.0001)
    
    y_h = 220 - ((h - l) / max_rango) * 180
    y_l = 220 - ((l - l) / max_rango) * 180
    y_o = 220 - ((o - l) / max_rango) * 180
    y_c = 220 - ((c - l) / max_rango) * 180
    
    canvas_vela.create_line(100, y_h, 100, y_l, fill=color_v, width=3)
    y_t, y_b = min(y_o, y_c), max(y_o, y_c)
    if abs(y_t - y_b) < 4: y_b = y_t + 4
    canvas_vela.create_rectangle(65, y_t, 135, y_b, fill=color_v, outline=color_v)
    
    def cerrar_y_actualizar():
        popup.destroy()
        actualizar_barra_superior()
        
    tk.Button(popup, text="CONTINUAR →", bg="#ff9900", fg="black", font=("Arial", 11, "bold"), command=cerrar_y_actualizar).pack(side="bottom", fill="x", padx=20, pady=20)

def revelar_siguiente_vela():
    global INDICE_ACTUAL
    if INDICE_ACTUAL < len(DF_MERCADO) - 1:
        INDICE_ACTUAL += 1
        slider_scroll.set(INDICE_ACTUAL)
        fila_siguiente = DF_MERCADO.iloc[INDICE_ACTUAL]
        o, h, l, c = fila_siguiente["Open"], fila_siguiente["High"], fila_siguiente["Low"], fila_siguiente["Close"]
        dibujar_mercado()
        
        gano_trade = (VOTO_USUARIO == "CALL" and c >= o) or (VOTO_USUARIO == "PUT" and c < o)
        lanzar_popup_resultado(gano_trade, o, h, l, c)
        

        
        btn_play.config(state="normal")
        btn_siguiente.config(state="disabled", bg="#30363d", fg="white")

# =====================================================================
# 🕒 ANIMACIÓN EN VIVO ESCALADA (PROPORCIÓN DE PRECIOS BROKER REAL)
# =====================================================================
def reproducir_linea_en_vivo():
    global ANIMANDO, TICKS_ACTUALES, VOTO_USUARIO
    if ANIMANDO or INDICE_ACTUAL >= len(DF_MERCADO): return
    ANIMANDO = True
    VOTO_USUARIO = None
    btn_play.config(state="disabled")
    slider_scroll.config(state="disabled")
    
    fila_actual = DF_MERCADO.iloc[INDICE_ACTUAL]
    o = fila_actual["Open"]
    h_v = fila_actual["High"]
    l_v = fila_actual["Low"]
    c_v = fila_actual["Close"]
    hora_actual_str = fila_actual["Hora"]
    
    h, m = map(int, hora_actual_str.split(":"))
    dt_objeto = datetime(2026, 10, 3, h, m)
    dt_cierre = dt_objeto + timedelta(minutes=1)

    if "Ticks_60s" in fila_actual and pd.notna(fila_actual["Ticks_60s"]):
        ticks_totales = [float(t) for t in str(fila_actual["Ticks_60s"]).split(";")]
    else:
        ticks_totales = [o]
        precio_p = o
        for seg in range(1, 59):
            factor = (c_v - precio_p) / (60 - seg)
            precio_p += factor + random.uniform(-0.00003, 0.00003)
            precio_p = max(l_v, min(h_v, precio_p))
            ticks_totales.append(precio_p)
        ticks_totales.append(c_v)

    for seg in range(1, 61):
        TICKS_ACTUALES = ticks_totales[:seg]
        
        ax_linea.clear()
        ax_linea.set_facecolor("#0d1117")
        ax_linea.tick_params(colors="#8b949e", labelsize=9)
        ax_linea.grid(color="#21262d", linestyle="--", linewidth=0.5)
        for spine in ax_linea.spines.values(): 
            spine.set_color("#30363d")
        
        ax_linea.set_title("Microestructura IQ Option (0-60s)", color="white", fontsize=11, fontweight="bold")
        ax_linea.set_xlim(0, 59)
        
        ax_linea.set_xticks([0, 30, 59])
        ax_linea.set_xticklabels([dt_objeto.strftime("%H:%M:00"), dt_objeto.strftime("%H:%M:30"), dt_cierre.strftime("%H:%M:00")])
        
        # Graficar línea blanca premium fluida
        ax_linea.plot(range(len(TICKS_ACTUALES)), TICKS_ACTUALES, color="#f5d109", linewidth=1.0)
        
        for y_val in LINEAS_DISEÑO:
            ax_linea.axhline(y=y_val, color="#ff007f", linestyle="-", linewidth=1.2)
            
        # CALIBRACIÓN DE ESCALA REALISTA: Evita el bug de la línea muerta arriba
        margen = (h_v - l_v) * 0.05 if (h_v - l_v) > 0 else 0.0001
        ax_linea.set_ylim(l_v - margen, h_v + margen)
        
        if len(ax_velas.patches) > 0:
            try: ax_velas.patches[-1].remove()
            except: pass
            
        precio_ahora = TICKS_ACTUALES[-1]
        color_d = "#2ea44f" if precio_ahora >= o else "#da3637"
        ax_velas.bar(INDICE_ACTUAL, precio_ahora - o, bottom=o, color=color_d, width=0.6)
        
        canvas.draw_idle()
        root.update()
        time.sleep(0.95) 
        
    ANIMANDO = False
    slider_scroll.config(state="normal")
    btn_call.config(state="normal")
    btn_put.config(state="normal")

# =====================================================================
# 🖥️ CONSTRUCCIÓN INTERFAZ VISUAL NATIVA
# =====================================================================
root = tk.Tk()
root.title("Entrenador ACCIÓN DE PRECIO - Sincronizado IQ Option")
root.geometry("1350x770")
root.configure(bg="#0d1117")

panel_sup = tk.Frame(root, bg="#161b22", height=50)
panel_sup.pack(fill="x", side="top", padx=5, pady=5)

lbl_info = tk.Label(panel_sup, text="Modo: Sincronizando relojes históricos...", fg="#ff9900", bg="#161b22", font=("Arial", 11, "bold"))
lbl_info.pack(side="left", padx=20, pady=10)

btn_random = tk.Button(root, text="🎲 RANDOM CONTEXTO", bg="#30363d", fg="white", font=("Arial", 10, "bold"), command=seleccionar_contexto_random)
btn_random.place(in_=panel_sup, relx=1.0, rely=0.5, anchor="e", x=-10)

btn_dibujo = tk.Button(root, text="✏️ MARCAR ZONAS", bg="#30363d", fg="white", font=("Arial", 10, "bold"), command=toggle_modo_dibujo)
btn_dibujo.place(in_=panel_sup, relx=1.0, rely=0.5, anchor="e", x=-180)

panel_inf = tk.Frame(root, bg="#161b22", height=80)
panel_inf.pack(fill="x", side="bottom", padx=5, pady=5)

btn_play = tk.Button(panel_inf, text="▶ REPRODUCIR 60s", bg="#ff9900", fg="black", font=("Arial", 11, "bold"), width=18, command=reproducir_linea_en_vivo)
btn_play.pack(side="left", padx=30, pady=20)

btn_call = tk.Button(panel_inf, text="↑ CALL", bg="#00b050", fg="white", activebackground="#008030", activeforeground="white", font=("Arial", 12, "bold"), width=14, bd=0, cursor="hand2", state="disabled", command=lambda: registrar_voto("CALL"))
btn_call.pack(side="left", padx=20, pady=20)

btn_put = tk.Button(panel_inf, text="↓ PUT", bg="#ff3333", fg="white", activebackground="#c02020", activeforeground="white", font=("Arial", 12, "bold"), width=14, bd=0, cursor="hand2", state="disabled", command=lambda: registrar_voto("PUT"))
btn_put.pack(side="left", padx=10, pady=20)

btn_siguiente = tk.Button(panel_inf, text="REVELAR RESULTADO →", bg="#30363d", fg="white", font=("Arial", 11, "bold"), width=22, state="disabled", command=revelar_siguiente_vela)
btn_siguiente.pack(side="right", padx=30, pady=20)

maximo_slider = max(RANGO_ZOOM + 1, len(DF_MERCADO) - 1)
slider_scroll = tk.Scale(root, from_=RANGO_ZOOM, to=maximo_slider, orient="horizontal", bg="#161b22", fg="#8b949e", highlightthickness=0, label="🎚️ RECORRER HISTORIAL (ADAPTATIVO REAL)", command=scroll_historial_nativo)
slider_scroll.set(INDICE_ACTUAL)
slider_scroll.pack(fill="x", side="bottom", padx=15, pady=2)

panel_central = tk.Frame(root, bg="#0d1117")
panel_central.pack(fill="both", expand=True, padx=10, pady=2)

fig, (ax_velas, ax_linea) = plt.subplots(1, 2, figsize=(12, 5), facecolor="#0d1117")
canvas = FigureCanvasTkAgg(fig, master=panel_central)
canvas.get_tk_widget().pack(fill="both", expand=True)

fig.canvas.mpl_connect('button_press_event', on_click_grafico)
fig.canvas.mpl_connect('scroll_event', zoom_rueda_mouse)

dibujar_mercado()
root.mainloop()
