import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

# Cargar entorno
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(env_path)

# Asegurar importación de calendar_manager
import sys
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import calendar_manager

# Importar herramientas
from agent import consultar_e_sugerir_horas, ejecutar_reserva_cita, SYSTEM_PROMPT_CONTENT

tools = [consultar_e_sugerir_horas, ejecutar_reserva_cita]
tools_dict = {tool.name: tool for tool in tools}

# Instanciar LLM
llm = ChatOpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("GITHUB_TOKEN"),
    model="gpt-4o-mini",
    temperature=0.3
).bind_tools(tools)

# Limpiar agenda antes del test para asegurar un estado conocido
calendario = calendar_manager.cargar_calendario()
# Asegurarnos de que los slots de la mañana del martes 26 de mayo estén disponibles para que el test sea determinista
for slot in ["09:30", "09:45", "10:00", "10:15", "10:30", "10:45", "11:00", "11:15", "11:30", "11:45"]:
    calendario["2026-05-26"][slot]["estado"] = "disponible"
    calendario["2026-05-26"][slot]["paciente"] = None
calendar_manager.guardar_calendario(calendario)

historial = [SystemMessage(content=SYSTEM_PROMPT_CONTENT)]

def interactuar(mensaje_usuario):
    if mensaje_usuario:
        print(f"\n[Paciente]: {mensaje_usuario}")
        historial.append(HumanMessage(content=mensaje_usuario))
    
    response = llm.invoke(historial)
    
    while response.tool_calls:
        historial.append(response)
        for tool_call in response.tool_calls:
            name = tool_call["name"]
            args = tool_call["args"]
            call_id = tool_call["id"]
            
            print(f"   -> [EJECUTANDO TOOL: {name} con args {args}]")
            output = tools_dict[name].invoke(args)
            print(f"      [RESULTADO TOOL]: {output}")
            
            historial.append(ToolMessage(content=str(output), tool_call_id=call_id))
            
        response = llm.invoke(historial)
        
    historial.append(response)
    print(f"[Plaza Dent Bot]: {response.content}")
    return response.content

def main():
    print("=========================================================")
    print("   INICIANDO TEST END-TO-END DE AGENTE DE CITAS DENTALES  ")
    print("=========================================================")
    
    # 1. Saludo inicial
    print("\n--- PASO 1: SALUDO INICIAL ---")
    interactuar(None)
    
    # 2. Paciente pregunta por promoción de limpieza
    print("\n--- PASO 2: CONSULTA POR LIMPIEZA ---")
    interactuar("Hola, me gustaria saber mas de la promocion de limpieza dental")
    
    # 3. Paciente indica qué día prefiere
    print("\n--- PASO 3: SOLICITUD DE DIA ---")
    interactuar("Me acomoda agendar para el martes por favor")
    
    # 4. Paciente elige la opción de las 10:30 hrs
    print("\n--- PASO 4: SELECCION DE OPCION ---")
    interactuar("Prefiero la opcion de las 10:30 hrs")
    
    # 5. Paciente da su nombre para cerrar la reserva
    print("\n--- PASO 5: REGISTRO DE NOMBRE Y RESERVA ---")
    interactuar("Mi nombre completo es Alejandra Silva")
    
    # 6. Validar persistencia en base de datos
    print("\n--- PASO 6: VALIDACION DE PERSISTENCIA EN BD ---")
    cal_actualizado = calendar_manager.cargar_calendario()
    
    all_booked = True
    slots_test = ["10:30", "10:45", "11:00", "11:15"]
    print("Estado de los slots de 10:30 a 11:15 en 2026-05-26 en calendar.json:")
    for slot in slots_test:
        slot_data = cal_actualizado["2026-05-26"][slot]
        print(f"Slot {slot}: {slot_data}")
        if slot_data["estado"] != "ocupado" or slot_data["paciente"] != "Alejandra Silva":
            all_booked = False
            
    if all_booked:
        print("\n[TEST COMPLETADO EXITOSAMENTE]")
        print("El agente se comunico amable y correctamente, calculo la duracion de 60 minutos para la limpieza dental, bloqueo los 4 bloques contiguos en la agenda y persistio la reserva de Alejandra Silva en la base de datos.")
    else:
        print("\n[TEST FALLIDO]")
        print("Los slots reservados en la base de datos no coinciden con las celdas esperadas para un bloque de 60 minutos.")

if __name__ == "__main__":
    main()
