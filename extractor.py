from iqoptionapi.stable_api import IQ_Option
import csv
import time

# 1. Configuración de Acceso (Usa tu cuenta Demo/Práctica por seguridad)
API = IQ_Option("agustingodoy207@gmail.com", "*$Filiberto15$*")
check, reason = API.connect()

if not check:
    print("Error al conectar con el broker:", reason)
    exit()

print("¡Conectado con éxito a IQ Option!")

# 2. Configurar el activo (Si es fin de semana, usa "EURUSD-OTC")
ACTIVO = "EURUSD-OTC" 
TIMEFRAME = 60   # Velas de 1 minuto (60 segundos)
CANTIDAD = 500   # Número de velas hacia atrás

print(f"Descargando {CANTIDAD} velas de {ACTIVO}...")

# 3. Descarga de datos históricos agregando el timestamp actual del servidor
# El formato obligatorio es: ACTIVES, interval, count, endtime
velas = API.get_candles(ACTIVO, TIMEFRAME, CANTIDAD, time.time())

# 4. Guardar directamente en el archivo que usa tu simulador
with open("datos_broker.csv", "w", newline="") as f:
    w = csv.writer(f)
    # Encabezados con el formato exacto que espera tu interfaz de simulación
    w.writerow(["Fecha", "Hora", "Open", "High", "Low", "Close"])
    
    for v in velas:
        # Convertir el timestamp del broker en formato de Fecha y Hora legible
        estructura_tiempo = time.localtime(v["from"])
        fecha_legible = time.strftime("%Y-%m-%d", estructura_tiempo)
        hora_legible = time.strftime("%H:%M", estructura_tiempo)
        
        # Escribir la fila alineada con el Lector Universal
        w.writerow([
            fecha_legible, 
            hora_legible, 
            v["open"], 
            v["max"], 
            v["min"], 
            v["close"]
        ])

print(f"¡Listo! Se guardaron {len(velas)} velas reales en 'datos_broker.csv'.")
print("Ya podés abrir tu simulator.py para entrenar con este mercado real.")
