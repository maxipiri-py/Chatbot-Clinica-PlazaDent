import json
import os

# Determinar la ruta absoluta al archivo calendar.json en el mismo directorio que este script
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calendar.json")

def cargar_calendario():
    """Carga los datos del calendario desde el archivo JSON."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"No se encontro el archivo de base de datos en {DB_PATH}")
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_calendario(data):
    """Guarda los datos del calendario en el archivo JSON."""
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def obtener_horas_disponibles(fecha):
    """Retorna una lista de horas disponibles para una fecha especifica."""
    calendario = cargar_calendario()
    if fecha not in calendario:
        return []
    
    horas = calendario[fecha]
    libres = []
    for hora, info in horas.items():
        if info["estado"] == "disponible":
            libres.append(hora)
    return libres

def sugerir_horas(fecha_preferida=None):
    """
    Sugiere hasta 3 opciones de citas disponibles.
    Si se especifica fecha_preferida, busca primero en ese dia. 
    Si no hay suficientes (menos de 3) en ese dia, busca en los dias siguientes de la semana.
    Si no se especifica fecha_preferida, busca los primeros 3 espacios libres de toda la semana.
    Retorna una lista de diccionarios con {'fecha': ..., 'hora': ...}
    """
    calendario = cargar_calendario()
    sugerencias = []
    
    # Ordenar las fechas cronologicamente
    fechas_ordenadas = sorted(list(calendario.keys()))
    
    if not fechas_ordenadas:
        return []
        
    # Si hay una fecha preferida, colocarla primero en la busqueda
    busqueda_fechas = []
    if fecha_preferida and fecha_preferida in calendario:
        busqueda_fechas.append(fecha_preferida)
        # Anadir el resto de las fechas despues de la preferida
        for f in fechas_ordenadas:
            if f != fecha_preferida:
                busqueda_fechas.append(f)
    else:
        busqueda_fechas = fechas_ordenadas
        
    # Recorrer las fechas para recolectar hasta 3 slots libres
    for f in busqueda_fechas:
        horas = calendario[f]
        # Ordenar las horas
        horas_ordenadas = sorted(list(horas.keys()))
        for h in horas_ordenadas:
            if horas[h]["estado"] == "disponible":
                sugerencias.append({
                    "fecha": f,
                    "hora": h
                })
                if len(sugerencias) == 3:
                    return sugerencias
                    
    return sugerencias

def reservar_hora(fecha, hora, nombre_paciente):
    """
    Intenta reservar una cita para una fecha y hora especifica.
    Si tiene exito, actualiza la base de datos y retorna un mensaje de confirmacion.
    De lo contrario, retorna un mensaje de error.
    """
    calendario = cargar_calendario()
    
    if fecha not in calendario:
        return f"Error: La fecha '{fecha}' no es valida en nuestro sistema."
        
    if hora not in calendario[fecha]:
        return f"Error: La hora '{hora}' no existe para la fecha {fecha}."
        
    slot = calendario[fecha][hora]
    if slot["estado"] == "ocupado":
        return f"Lo siento, la hora {hora} del dia {fecha} ya se encuentra ocupada por otro paciente."
        
    # Realizar la reserva
    slot["estado"] = "ocupado"
    slot["paciente"] = nombre_paciente
    
    guardar_calendario(calendario)
    return f"Reserva exitosa: Cita agendada para el dia {fecha} a las {hora} a nombre de {nombre_paciente}."

if __name__ == "__main__":
    # Test sencillo de funcionamiento de la base de datos
    print("=== PROBANDO GESTOR DE CALENDARIO ===")
    print("Sugerencias iniciales:")
    print(sugerir_horas())
    print("\nSugerencias para el 2026-05-28 (un dia muy ocupado):")
    print(sugerir_horas("2026-05-28"))
    
    # Reservar una hora libre de prueba
    print("\nReservando hora de prueba:")
    res = reservar_hora("2026-05-29", "09:00", "Sebastian Lopez")
    print(res)
    
    # Comprobar que se actualizo y ya no se sugiere
    print("\nSugerencias despues de reservar el primer slot del 2026-05-29:")
    print(sugerir_horas("2026-05-29"))
    
    # Restaurar la reserva de prueba para dejar la base de datos limpia
    calendario = cargar_calendario()
    calendario["2026-05-29"]["09:00"]["estado"] = "disponible"
    calendario["2026-05-29"]["09:00"]["paciente"] = None
    guardar_calendario(calendario)
    print("\nBase de datos restaurada y limpia.")
