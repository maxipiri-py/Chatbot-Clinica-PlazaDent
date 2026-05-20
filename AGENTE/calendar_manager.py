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

def parsed_minutes(hora_str):
    """Convierte una hora en formato HH:MM a minutos desde la medianoche."""
    h, m = map(int, hora_str.split(":"))
    return h * 60 + m

def sugerir_horas(fecha_preferida=None, duracion_minutos=15):
    """
    Sugiere hasta 3 opciones de citas disponibles de una duracion especificada en minutos.
    Busca bloques de 15 minutos contiguos y libres.
    
    Si se especifica fecha_preferida, busca primero en ese dia. 
    Si no hay suficientes (menos de 3) en ese dia, busca en los dias siguientes de la semana.
    Si no se especifica fecha_preferida, busca en toda la semana de forma cronologica.
    
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
        # Añadir el resto de las fechas despues de la preferida
        for f in fechas_ordenadas:
            if f != fecha_preferida:
                busqueda_fechas.append(f)
    else:
        busqueda_fechas = fechas_ordenadas
        
    n_blocks = duracion_minutos // 15
    
    # Recorrer las fechas para recolectar hasta 3 slots libres
    for f in busqueda_fechas:
        slots = sorted(list(calendario[f].keys())) # ["09:00", "09:15", ...]
        i = 0
        while i <= len(slots) - n_blocks:
            is_free = True
            
            # Verificar si todos los n_blocks consecutivos estan disponibles
            for j in range(n_blocks):
                current_slot = slots[i + j]
                if calendario[f][current_slot]["estado"] != "disponible":
                    is_free = False
                    break
                    
            # Verificar si son contiguos en tiempo
            if is_free:
                t_first = parsed_minutes(slots[i])
                t_last = parsed_minutes(slots[i + n_blocks - 1])
                if (t_last - t_first) != (n_blocks - 1) * 15:
                    is_free = False
                    
            if is_free:
                sugerencias.append({
                    "fecha": f,
                    "hora": slots[i]
                })
                if len(sugerencias) == 3:
                    return sugerencias
                # Avanzar la i para evitar sugerir slots que se solapen en la misma sugerencia
                i += n_blocks
            else:
                i += 1
                
    return sugerencias

def reservar_hora(fecha, hora_inicio, duracion_minutos, nombre_paciente):
    """
    Intenta reservar una cita para una fecha, hora de inicio y duracion especifica.
    Bloquea los slots contiguos de 15 minutos necesarios en la base de datos.
    """
    calendario = cargar_calendario()
    
    if fecha not in calendario:
        return f"Error: La fecha '{fecha}' no es valida en nuestro sistema."
        
    slots = sorted(list(calendario[fecha].keys()))
    if hora_inicio not in slots:
        return f"Error: La hora '{hora_inicio}' no existe para la fecha {fecha}."
        
    n_blocks = duracion_minutos // 15
    start_idx = slots.index(hora_inicio)
    
    if start_idx + n_blocks > len(slots):
        return f"Error: No hay suficiente tiempo al final del dia para una cita de {duracion_minutos} minutos."
        
    # Verificar disponibilidad
    target_slots = []
    for j in range(n_blocks):
        current_slot = slots[start_idx + j]
        target_slots.append(current_slot)
        if calendario[fecha][current_slot]["estado"] == "ocupado":
            ocupante = calendario[fecha][current_slot].get("paciente", "otro paciente")
            return f"Lo siento, la hora {hora_inicio} de duracion {duracion_minutos} minutos no se puede reservar porque interfiere con una cita de {ocupante}."
            
    # Verificar contiguidad
    t_first = parsed_minutes(slots[start_idx])
    t_last = parsed_minutes(slots[start_idx + n_blocks - 1])
    if (t_last - t_first) != (n_blocks - 1) * 15:
        return f"Error: Los bloques de tiempo requeridos no son contiguos."
        
    # Proceder a ocupar todos los slots
    for current_slot in target_slots:
        calendario[fecha][current_slot]["estado"] = "ocupado"
        calendario[fecha][current_slot]["paciente"] = nombre_paciente
        
    guardar_calendario(calendario)
    return f"Reserva exitosa: Cita de {duracion_minutos} minutos agendada para el dia {fecha} a las {hora_inicio} a nombre de {nombre_paciente}."

if __name__ == "__main__":
    # Test sencillo de funcionamiento de la base de datos de 15 min
    print("=== PROBANDO GESTOR DE CALENDARIO POR BLOQUES DE 15 MIN ===")
    
    print("\nSugerencias iniciales para limpieza (60 min):")
    print(sugerir_horas(duracion_minutos=60))
    
    print("\nSugerencias iniciales para cirugia (90 min):")
    print(sugerir_horas(duracion_minutos=90))
    
    print("\nSugerencias iniciales para evaluacion protesis (15 min):")
    print(sugerir_horas(duracion_minutos=15))
    
    # Reservar una cita de prueba de 60 minutos
    print("\nReservando cita de prueba de 60 minutos (Limpieza):")
    res = reservar_hora("2026-05-29", "09:00", 60, "Sebastian Lopez")
    print(res)
    
    # Comprobar que se actualizo y ya no se sugiere
    print("\nSugerencias para limpieza en el 2026-05-29 despues de la reserva:")
    print(sugerir_horas("2026-05-29", duracion_minutos=60))
    
    # Restaurar la reserva de prueba para dejar la base de datos limpia
    calendario = cargar_calendario()
    for m in [0, 15, 30, 45]:
        calendario["2026-05-29"][f"09:{m:02d}"]["estado"] = "disponible"
        calendario["2026-05-29"][f"09:{m:02d}"]["paciente"] = None
    guardar_calendario(calendario)
    print("\nBase de datos restaurada y limpia.")
