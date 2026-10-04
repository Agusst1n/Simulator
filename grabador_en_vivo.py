from iqoptionapi.stable_api import IQ_Option
import csv
import time
import os
import random
from datetime import datetime, timedelta

# =====================================================================
# 🔐 CONFIGURACIÓN DE ACCESO
# =====================================================================
CORREO = "TU_CORREO.COM"
PASSWORD = "TU_CONTRASEÑA"
ACTIVO = "EURUSD-OTC"  

API = IQ_Option(CORREO, PASSWORD)
check, reason = API.connect()

if not check:
    print(f"[-] Error de conexión: {reason}")
    exit()

print(f"[+] Conectado con éxito. Grabando {ACTIVO} con Motor de Alta Frecuencia Cronológica...")

ARCHIVO_SALIDA = "datos_broker.csv"
if not os.path.exists(ARCHIVO_SALIDA):
    with open(ARCHIVO_SALIDA, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Fecha", "Hora", "Timestamp", "Open", "High", "Low", "Close", "Ticks_60s"])

# Arrancar la transmisión de datos en vivo nativa a máxima velocidad
API.start_candles_stream(ACTIVO, 1, 10)
time.sleep(2)

print("[*] Interceptando los 60 segundos exactos en tiempo real... No cierres esta ventana.")

# Contenedor rígido indexado por cada segundo real del 0 al 59
ticks_cronologicos = [None] * 60
minuto_actual = datetime.now().minute

try:
    while True:
        velas_1s = API.get_realtime_candles(ACTIVO, 1)
        
        if velas_1s:
            # Ordenar por estampa de tiempo cronológica estricta
            for ts in sorted(velas_1s.keys()):
                precio_tick = velas_1s[ts]["close"]
                dt_tick = datetime.fromtimestamp(ts)
                
                # Sincronizar el casillero correspondiente al segundo actual (0 al 59)
                segundo_actual = dt_tick.second
                
                if dt_tick.minute == minuto_actual:
                    ticks_cronologicos[segundo_actual] = precio_tick
                else:
                    # ¡Cambió el minuto financiero en el broker! Procesamos el bloque de 60s
                    # Filtrar que tengamos datos reales cargados en memoria
                    ticks_validos = [t for t in ticks_cronologicos if t is not None]
                    
                    if len(ticks_validos) > 5:
                        o_v = ticks_validos[0]
                        c_v = ticks_validos[-1]
                        h_v = max(ticks_validos)
                        l_v = min(ticks_validos)
                        
                        dt_final = datetime.now() - timedelta(minutes=1)
                        fecha_str = dt_final.strftime("%Y-%m-%d")
                        hora_str = dt_final.strftime("%H:%M")
                        ts_str = dt_final.timestamp()
                        
                        # --- INTERPOLACIÓN ESTRICTA ANTI-HUECOS ---
                        # Si algún segundo se perdió por lag de internet, rellena el casillero
                        # de forma fluida basándose en la tendencia del segundo anterior inmediato
                        precio_arrastre = o_v
                        for s in range(60):
                            if ticks_cronologicos[s] is None:
                                ticks_cronologicos[s] = precio_arrastre
                            else:
                                precio_arrastre = ticks_cronologicos[s]
                        
                        ticks_cadena = ";".join([f"{t:.5f}" for t in ticks_cronologicos])
                        
                        with open(ARCHIVO_SALIDA, "a", newline="") as f:
                            writer = csv.writer(f)
                            writer.writerow([fecha_str, hora_str, ts_str, f"{o_v:.5f}", f"{h_v:.5f}", f"{l_v:.5f}", f"{c_v:.5f}", ticks_cadena])
                        
                        print(f"[REGISTRO DE ALTA FIDELIDAD OK] Minuto {hora_str} guardado con los 60 segundos exactos (00-59).")
                    
                    # Resetear el casillero rígido para el nuevo minuto entrante
                    ticks_cronologicos = [None] * 60
                    ticks_cronologicos[segundo_actual] = precio_tick  # <-- ¡CORREGIDO AQUÍ!
                    minuto_actual = dt_tick.minute
                    
        # Pausa ultracorta de ráfaga para capturar los hilos sin saltarse ningún segundo
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\n[-] Grabación finalizada de forma segura.")
