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
        precio = 1.1150  
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

DF_MERCADO = DF_MERCADO.drop_duplicates(subset=["Hora"]).reset_index(drop=True)

if len(DF_MERCADO) > 120:
    DF_MERCADO = DF_MERCADO.tail(120).reset_index(drop=True)

for col in ["Open", "High", "Low", "Close"]:
    DF_MERCADO[col] = DF_MERCADO[col].astype(float)

TOTAL_VELAS_REGISTRADAS = len(DF_MERCADO)
RANGO_ZOOM = 45  
INDICE_ACTUAL = max(RANGO_ZOOM + 1, TOTAL_VELAS_REGISTRADAS - 2)

if INDICE_ACTUAL >= TOTAL_VELAS_REGISTRADAS:
    INDICE_ACTUAL = TOTAL_VELAS_REGISTRADAS - 1

DIVISA_ACTIVA = "EURUSD-OTC"

TICKS_ACTUALES = []
ANIMANDO = False
VOTO_USUARIO = None
LINEAS_DISEÑO = [] 
MODO_DIBUJO_ACTIVO = False
BARRA_DINAMICA_ACTIVA = None  
ELEMENTOS_DINAMICOS_VELA = []

TRADES_GANADOS = 0
TRADES_PERDIDOS = 0

COLOR_FONDO_PRO = "#0b0e14"
COLOR_ALCISTA = "#00c2a6"  
COLOR_BAJISTA = "#ff4a5a"  

def obtener_hora_formateada(x):
    idx = int(round(x))
    if idx < 0 or idx >= len(DF_MERCADO): return ""
    return DF_MERCADO.iloc[idx]["Hora"]

# =====================================================================
# 📉 MOTOR GRÁFICO MAXIMIZADO PROFESIONAL (REPARADO SIN LÍNEA PREVIA)
# =====================================================================
def configurar_eje_maximizado(ax, titulo):
    ax.set_facecolor(COLOR_FONDO_PRO)
    ax.set_title(titulo, color="#4e5663", fontsize=9, fontweight="bold", loc="left", pad=10)
    ax.tick_params(colors="#4e5663", labelsize=8)
    ax.grid(color="#161a24", linestyle="-", linewidth=0.5)
    ax.yaxis.set_visible(False)
    for spine in ax.spines.values():
        spine.set_color("#161a24")

def dibujar_mercado():
    global BARRA_DINAMICA_ACTIVA, ELEMENTOS_DINAMICOS_VELA
    BARRA_DINAMICA_ACTIVA = None  
    ELEMENTOS_DINAMICOS_VELA = []
    
    ax_velas.clear()
    ax_linea.clear()
    
    configurar_eje_maximizado(ax_velas, f"  ● VELAS M1 | {DIVISA_ACTIVA}")
    configurar_eje_maximizado(ax_linea, "  ● MICROESTRUCTURA IQ OPTION (60 TICKS)")
    
    df_previo = DF_MERCADO.iloc[:INDICE_ACTUAL]
    for i in range(len(df_previo)):
        fila = df_previo.iloc[i]
        o, h, l, c = fila["Open"], fila["High"], fila["Low"], fila["Close"]
        color = COLOR_ALCISTA if c >= o else COLOR_BAJISTA
        ax_velas.plot([i, i], [l, h], color=color, linewidth=1.2)
        ax_velas.bar(i, c - o, bottom=o, color=color, width=0.6, edgecolor=color, linewidth=0.1)

    ticks_x = list(range(0, len(df_previo), max(1, len(df_previo)//5)))
    etiquetas_x = [obtener_hora_formateada(t) for t in ticks_x]
    ax_velas.set_xticks(ticks_x)
    ax_velas.set_xticklabels(etiquetas_x)
    
    for y_val in LINEAS_DISEÑO:
        ax_velas.axhline(y=y_val, color="#ff007f", linestyle="--", linewidth=1.0, alpha=0.7)
        
    idx_inicio = max(0, INDICE_ACTUAL - RANGO_ZOOM)
    ax_velas.set_xlim(idx_inicio - 0.5, INDICE_ACTUAL + 0.5)
    
    velas_visibles = df_previo.iloc[idx_inicio:INDICE_ACTUAL]
    if not velas_visibles.empty:
        ax_velas.set_ylim(velas_visibles["Low"].min() * 0.9998, velas_visibles["High"].max() * 1.0002)
    
    # --- LA LÍNEA DERECHA ARRANCA COMPLETAMENTE VACÍA ---
    ax_linea.set_xlim(0, 59)
    fila_v = DF_MERCADO.iloc[INDICE_ACTUAL]
    
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
    lbl_info.config(text=f" 📂 DIVISA: {DIVISA_ACTIVA}   |   🕦 VELA: {fila_v['Hora']}   |   🎯 EFECTIVIDAD: {win_rate:.1f}% ({TRADES_GANADOS}/{total_trades})")

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
    btn_dibujo.config(bg="#ff007f" if MODO_DIBUJO_ACTIVO else "#1c212c", text="✏️ DIBUJO: ACTIVO" if MODO_DIBUJO_ACTIVO else "✏️ MARCAR ZONAS")

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
    popup.configure(bg=COLOR_FONDO_PRO)
    popup.resizable(False, False)
    popup.transient(root)
    popup.grab_set()
    
    color_t = COLOR_ALCISTA if gano else COLOR_BAJITA
    tk.Label(popup, text="🎯 ¡OPERACIÓN GANADA!" if gano else "❌ OPERACIÓN PERDIDA", fg=color_t, bg=COLOR_FONDO_PRO, font=("Arial", 15, "bold")).pack(pady=15)
    
    canvas_vela = tk.Canvas(popup, width=220, height=240, bg="#11151e", highlightthickness=1, highlightbackground="#1c212c")
    canvas_vela.pack(pady=5)
    
    color_v = COLOR_ALCISTA if c >= o else COLOR_BAJITA
    max_rango = max(h - l, 0.0001)
    
    y_h = 220 - ((h - l) / max_rango) * 180
    y_l = 220 - ((l - l) / max_rango) * 180
    y_o = 220 - ((o - l) / max_rango) * 180
    y_c = 220 - ((c - l) / max_rango) * 180
    
    canvas_vela.create_line(110, y_h, 110, y_l, fill=color_v, width=3)
    y_t, y_b = min(y_o, y_c), max(y_o, y_c)
    if abs(y_t - y_b) < 6: y_b = y_t + 6
    canvas_vela.create_rectangle(75, y_t, 145, y_b, fill=color_v, outline=color_v)
    
    tk.Label(popup, text=f"Apertura: {o:.5f}", fg="#8b949e", bg=COLOR_FONDO_PRO, font=("Courier", 10)).pack(pady=2)
    tk.Label(popup, text=f"Cierre: {c:.5f}", fg="white", bg=COLOR_FONDO_PRO, font=("Courier", 10, "bold")).pack(pady=2)
    
    def cerrar_y_actualizar():
        popup.destroy()
        actualizar_barra_superior()
        
    tk.Button(popup, text="SIGUIENTE VELA →", bg="#ff9900", fg="black", font=("Arial", 11, "bold"), bd=0, cursor="hand2", command=cerrar_y_actualizar).pack(side="bottom", fill="x", padx=30, pady=15)

def revelar_siguiente_vela():
    global INDICE_ACTUAL
    if INDICE_ACTUAL < len(DF_MERCADO) - 1:
        INDICE_ACTUAL += 1
        slider_scroll.set(INDICE_ACTUAL)
        fila_siguiente = DF_MERCADO.iloc[INDICE_ACTUAL]
        
        # Sincronización absoluta con mayúsculas de tu base real
        o = float(fila_siguiente["Open"])
        h = float(fila_siguiente["High"])
        l = float(fila_siguiente["Low"])
        c = float(fila_siguiente["Close"])
        
        dibujar_mercado()
        
        gano_trade = (VOTO_USUARIO == "CALL" and c >= o) or (VOTO_USUARIO == "PUT" and c < o)
        lanzar_popup_resultado(gano_trade, o, h, l, c)
        
        btn_play.config(state="normal")
        btn_siguiente.config(state="disabled", bg="#1c212c", fg="#8b949e")


# =====================================================================
# 🕒 ANIMACIÓN EN VIVO AISLADA (MECHAS DINÁMICAS EN VIVO + AMARILLO ORO)
# =====================================================================
def reproducir_linea_en_vivo():
    global ANIMANDO, TICKS_ACTUALES, VOTO_USUARIO, ELEMENTOS_DINAMICOS_VELA
    if ANIMANDO or INDICE_ACTUAL >= len(DF_MERCADO): return
    ANIMANDO = True
    
    # Bloquear botones operacionales durante el desarrollo de la microestructura
    btn_play.config(state="disabled")
    btn_repetir.config(state="disabled")
    btn_siguiente.config(state="disabled", bg="#1c212c", fg="#8b949e")
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

    max_alcanzado = o
    min_alcanzado = o

    for seg in range(1, 61):
        TICKS_ACTUALES = ticks_totales[:seg]
        
        ax_linea.clear()
        configurar_eje_maximizado(ax_linea, "  ● MICROESTRUCTURA IQ OPTION (60 TICKS)")
        ax_linea.set_xlim(0, 59)
        
        ax_linea.set_xticks([0, 30, 59])
        ax_linea.set_xticklabels([dt_objeto.strftime("%H:%M:00"), dt_objeto.strftime("%H:%M:30"), dt_cierre.strftime("%H:%M:00")])
        
        ax_linea.plot(range(len(TICKS_ACTUALES)), TICKS_ACTUALES, color="#ebba19", linewidth=1.0)
        
        for y_val in LINEAS_DISEÑO:
            ax_linea.axhline(y=y_val, color="#ff007f", linestyle="--", linewidth=1.0, alpha=0.7)
            
        margen = (h_v - l_v) * 0.05 if (h_v - l_v) > 0 else 0.0001
        ax_linea.set_ylim(l_v - margen, h_v + margen)
        
        precio_ahora = TICKS_ACTUALES[-1]
        color_d = COLOR_ALCISTA if precio_ahora >= o else COLOR_BAJISTA
        
        if precio_ahora > max_alcanzado: max_alcanzado = precio_ahora
        if precio_ahora < min_alcanzado: min_alcanzado = precio_ahora
        
        for elemento in ELEMENTOS_DINAMICOS_VELA:
            try: elemento.remove()
            except: pass
            
        ELEMENTOS_DINAMICOS_VELA = []
        
        mecha = ax_velas.plot([INDICE_ACTUAL, INDICE_ACTUAL], [min_alcanzado, max_alcanzado], color=color_d, linewidth=1.2)
        ELEMENTOS_DINAMICOS_VELA.append(mecha)
        
        cuerpo = ax_velas.bar(INDICE_ACTUAL, precio_ahora - o, bottom=o, color=color_d, width=0.6, edgecolor=color_d, linewidth=0.1, zorder=4)
        ELEMENTOS_DINAMICOS_VELA.append(cuerpo)
        
        canvas.draw_idle()
        root.update()
        time.sleep(0.55) 
        
    ANIMANDO = False
    slider_scroll.config(state="normal")
    btn_play.config(state="normal")
    btn_repetir.config(state="normal")
    
    # --- RECONEXIÓN CRÍTICA: Desbloquea CALL y PUT de forma limpia para recibir el voto del usuario ---
    btn_call.config(state="normal")
    btn_put.config(state="normal")

def repetir_vela_actual():
    if ANIMANDO: return
    dibujar_mercado()
    reproducir_linea_en_vivo()

# =====================================================================
# 🖥️ CONSTRUCCIÓN INTERFAZ VISUAL NATIVA MAXIMIZADA PREMIUM
# =====================================================================
root = tk.Tk()
root.title("Entrenador ACCIÓN DE PRECIO - Sincronizado IQ Option")
root.geometry("1350x770")
root.configure(bg=COLOR_FONDO_PRO)

panel_sup = tk.Frame(root, bg="#11151d", height=45)
panel_sup.pack(fill="x", side="top", padx=5, pady=3)

lbl_info = tk.Label(panel_sup, text="Modo: Sincronizando interfaces masivas...", fg="#e2e8f0", bg="#11151d", font=("Arial", 10, "bold"))
lbl_info.pack(side="left", padx=20, pady=10)

btn_random = tk.Button(root, text="🎲 RANDOM CONTEXTO", bg="#1c212c", fg="white", font=("Arial", 9, "bold"), bd=0, padx=12, pady=5, cursor="hand2", command=seleccionar_contexto_random)
btn_random.place(in_=panel_sup, relx=1.0, rely=0.5, anchor="e", x=-10)

btn_dibujo = tk.Button(root, text="✏️ MARCAR ZONAS", bg="#1c212c", fg="white", font=("Arial", 9, "bold"), bd=0, padx=12, pady=5, cursor="hand2", command=toggle_modo_dibujo)
btn_dibujo.place(in_=panel_sup, relx=1.0, rely=0.5, anchor="e", x=-180)

panel_inf = tk.Frame(root, bg="#11151d", height=70)
panel_inf.pack(fill="x", side="bottom", padx=5, pady=3)

btn_play = tk.Button(panel_inf, text="▶ REPRODUCIR 60s", bg="#ff9900", fg="black", font=("Arial", 10, "bold"), width=16, bd=0, cursor="hand2", command=reproducir_linea_en_vivo)
btn_play.pack(side="left", padx=25, pady=15)

btn_repetir = tk.Button(panel_inf, text="🔄 REPETIR VELA", bg="#3a3f4d", fg="white", font=("Arial", 10, "bold"), width=14, bd=0, cursor="hand2", command=repetir_vela_actual)
btn_repetir.pack(side="left", padx=10, pady=15)

btn_call = tk.Button(panel_inf, text="↑ CALL", bg=COLOR_ALCISTA, fg="white", activebackground="#009e86", activeforeground="white", font=("Arial", 11, "bold"), width=13, bd=0, cursor="hand2", state="disabled", command=lambda: registrar_voto("CALL"))
btn_call.pack(side="left", padx=15, pady=15)

COLOR_BAJITA = COLOR_BAJISTA
btn_put = tk.Button(panel_inf, text="↓ PUT", bg=COLOR_BAJISTA, fg="white", activebackground="#cf3240", activeforeground="white", font=("Arial", 11, "bold"), width=13, bd=0, cursor="hand2", state="disabled", command=lambda: registrar_voto("PUT"))
btn_put.pack(side="left", padx=10, pady=15)

btn_siguiente = tk.Button(panel_inf, text="REVELAR RESULTADO →", bg="#1c212c", fg="#8b949e", font=("Arial", 10, "bold"), width=20, bd=0, cursor="hand2", state="disabled", command=revelar_siguiente_vela)
btn_siguiente.pack(side="right", padx=25, pady=15)

maximo_slider = max(RANGO_ZOOM + 1, len(DF_MERCADO) - 1)
slider_scroll = tk.Scale(root, from_=RANGO_ZOOM, to=maximo_slider, orient="horizontal", bg="#11151d", fg="#8b949e", highlightthickness=0, troughcolor=COLOR_FONDO_PRO, font=("Arial", 8), label="🎚️ HISTORIAL DE OPERACIONES", command=scroll_historial_nativo)
slider_scroll.set(INDICE_ACTUAL)
slider_scroll.pack(fill="x", side="bottom", padx=15, pady=2)

panel_central = tk.Frame(root, bg=COLOR_FONDO_PRO)
panel_central.pack(fill="both", expand=True, padx=10, pady=2)

fig, (ax_velas, ax_linea) = plt.subplots(1, 2, figsize=(12, 5), facecolor=COLOR_FONDO_PRO)
fig.subplots_adjust(left=0.01, right=0.99, top=0.94, bottom=0.06, wspace=0.04)

canvas = FigureCanvasTkAgg(fig, master=panel_central)
canvas.get_tk_widget().pack(fill="both", expand=True)

fig.canvas.mpl_connect('button_press_event', on_click_grafico)
fig.canvas.mpl_connect('scroll_event', zoom_rueda_mouse)

dibujar_mercado()
root.mainloop()
