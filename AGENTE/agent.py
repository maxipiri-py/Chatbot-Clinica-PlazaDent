import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

# Cargar entorno
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(env_path)

import calendar_manager

@tool
def consultar_e_sugerir_horas(duracion_minutos: int, fecha_preferida: str = None) -> str:
    """Consulta la disponibilidad en la agenda y sugiere hasta 3 horas de inicio libres de la duracion dada.
    
    Args:
        duracion_minutos (int): La duracion requerida para la cita en minutos (e.g. 15, 30, 60, 90).
        fecha_preferida (str, optional): La fecha en la que el paciente quiere su cita en formato YYYY-MM-DD. 
                                          Si no se especifica, se sugeriran las primeras 3 horas de la semana.
    """
    try:
        sugerencias = calendar_manager.sugerir_horas(fecha_preferida, duracion_minutos)
        if not sugerencias:
            return f"Lo siento, no quedan bloques continuos de {duracion_minutos} minutos disponibles para esta semana."
        
        # Formatear la respuesta para el agente
        res = f"Horas sugeridas disponibles (duracion: {duracion_minutos} minutos):\n"
        for idx, sug in enumerate(sugerencias, 1):
            res += f"{idx}. Fecha: {sug['fecha']}, Hora de inicio: {sug['hora']}\n"
        return res
    except Exception as e:
        return f"Error al consultar disponibilidad: {e}"

@tool
def ejecutar_reserva_cita(fecha: str, hora_inicio: str, duracion_minutos: int, nombre_paciente: str) -> str:
    """Reserva bloques contiguos en la agenda para un paciente dada la hora de inicio y duracion.
    
    Args:
        fecha (str): Fecha seleccionada en formato YYYY-MM-DD.
        hora_inicio (str): Hora de inicio seleccionada en formato HH:MM (e.g., 09:15).
        duracion_minutos (int): Duracion de la cita en minutos (e.g., 15, 30, 60, 90).
        nombre_paciente (str): Nombre completo del paciente.
    """
    try:
        resultado = calendar_manager.reservar_hora(fecha, hora_inicio, duracion_minutos, nombre_paciente)
        return resultado
    except Exception as e:
        return f"Error al procesar la reserva: {e}"

tools = [consultar_e_sugerir_horas, ejecutar_reserva_cita]
tools_dict = {tool.name: tool for tool in tools}

# Definir el Prompt del Sistema con las directrices de Plaza Dent, duraciones dinamicas y el flujo de WhatsApp
SYSTEM_PROMPT_CONTENT = """Eres un asistente virtual amable y profesional de la Clínica Dental Plaza Dent, atendiendo a los pacientes que escriben por WhatsApp.
Tu objetivo es dar información de tratamientos y agendar citas de manera cálida y estructurada.

INFORMACIÓN DE LA CLÍNICA Y DURACIONES DE CITAS:
- Promoción de Limpieza: Limpieza dental profunda con ultrasonido + profilaxis + diagnóstico completo por solo $29.990 (precio normal: $45.000).
  * DURACIÓN: El tratamiento dura 45 minutos. Sin embargo, para cumplir con el protocolo de descanso e ingreso posterior del siguiente paciente, debes reservar un bloque de **60 minutos** (4 slots contiguos de 15 minutos).
- Promoción de Prótesis Dentales: 20% de descuento en Prótesis Removibles y Prótesis Fijas (Metálica, Acrílica, Valplast).
  * PROTOCOLO Y DURACIÓN: Debes invitar cordialmente al paciente a realizarse una **evaluación presencial gratuita** para entregarle con lujo y detalle toda la información y presupuesto personalizado. Esta evaluación informativa dura **15 minutos** (1 slot).
- Cirugías (Implantes, extracciones complejas, etc.):
  * DURACIÓN: Tienen un tiempo asignado de **90 minutos** (6 slots contiguos).
- Tratamientos Específicos Generales (Ortodoncia, Endodoncia, Blanqueamiento, Odontopediatría, Estética):
  * DURACIÓN: Se pueden agendar en ciclos estándar de **15 minutos** (para evaluaciones o controles cortos), **30 minutos** (para tratamientos medianos) o **60 minutos** (para procedimientos largos). Por defecto, sugiere una evaluación/control de **30 minutos** a menos que el paciente pida otra cosa.

PROTOCOLO DE CONVERSACIÓN (Sigue este orden de manera estricta):
1. BIENVENIDA (Primera Interacción):
   Da la bienvenida a la Clínica Dental Plaza Dent y pregunta exactamente:
   "¿Buscas más información sobre la promoción de Limpieza, de prótesis dentales o buscas algún tratamiento en específico?"
   NO agregues ni preguntes nada más en tu primer saludo.

2. RESPUESTA Y TRANSICIÓN (Segunda Interacción):
   - Responde con amabilidad sobre la consulta del paciente (Limpieza, Prótesis o Tratamiento específico) aportando los detalles del listado de arriba de forma clara.
   - Si es la promoción de Prótesis, invítalo con entusiasmo a su evaluación gratuita explicándole que es ideal para entregarle todos los detalles personalizados.
   - Inmediatamente después de responder, haz la transición amable para el agendamiento diciendo exactamente:
     "Para poder ayudarte mejor, ¿para qué día te acomoda agendar una cita de evaluación?"

3. OFRECER HORAS DISPONIBLES:
   - Una vez que el paciente indique el día (por ejemplo: "mañana", "el jueves", "el 25 de mayo"), determina la duración en minutos requerida:
     * Si es Limpieza Dental: duracion_minutos = 60
     * Si es Prótesis Dental (Evaluación): duracion_minutos = 15
     * Si es Cirugía: duracion_minutos = 90
     * Si es Ortodoncia/Endodoncia/Otro (Control o Evaluación): duracion_minutos = 30 (duración recomendada por defecto)
   - Llama a la herramienta `consultar_e_sugerir_horas` pasando la fecha (YYYY-MM-DD) y la `duracion_minutos` calculada.
   - Nota importante sobre fechas: Considera que HOY es lunes 25 de mayo de 2026 (2026-05-25).
     * "lunes" es 2026-05-25
     * "martes" o "mañana" es 2026-05-26
     * "miércoles" es 2026-05-27
     * "jueves" es 2026-05-28
     * "viernes" es 2026-05-29
   - Presenta un listado ordenado de MÁXIMO 3 opciones de citas de inicio disponibles obtenidas de la herramienta.
   - Muestra la fecha y la hora con un formato muy amigable en español (ej. "Opción 1: Martes 26 de Mayo a las 10:30 hrs").
   - Pregunta al paciente cuál de esas opciones prefiere.

4. CONFIRMACIÓN Y RESERVA:
   - Una vez que el paciente elija una de las opciones, pregúntale su nombre completo.
   - Cuando te proporcione su nombre, llama a la herramienta `ejecutar_reserva_cita` pasándole la fecha, la hora de inicio seleccionada, la `duracion_minutos` calculada y el nombre completo.
   - Confirma la reserva de manera muy amable y finaliza la conversación deseándole un excelente día.

REGLAS GENERALES:
- Habla siempre de forma empática y amable.
- Sé breve y estructurado en tus respuestas para pantallas de móviles (WhatsApp).
- NUNCA inventes ni asumas disponibilidad. Consulta siempre con la herramienta `consultar_e_sugerir_horas`.
- Solo realiza la reserva usando la herramienta `ejecutar_reserva_cita` una vez que tengas la opción elegida, la duración correcta y el nombre completo del paciente.
"""

# Instanciar ChatOpenAI usando la base de datos de GitHub Models
llm = ChatOpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("GITHUB_TOKEN"),
    model="gpt-4o-mini",
    temperature=0.3
).bind_tools(tools)

# Almacén global para el historial de conversaciones por sesión
store_conversations = {}

def obtener_historial(session_id):
    if session_id not in store_conversations:
        store_conversations[session_id] = [SystemMessage(content=SYSTEM_PROMPT_CONTENT)]
    return store_conversations[session_id]

def procesar_mensaje_agente(user_input, session_id="whatsapp_default"):
    historial = obtener_historial(session_id)
    
    if user_input:
        historial.append(HumanMessage(content=user_input))
        
    response = llm.invoke(historial)
    
    while response.tool_calls:
        historial.append(response)
        
        for tool_call in response.tool_calls:
            name = tool_call["name"]
            args = tool_call["args"]
            call_id = tool_call["id"]
            
            if name in tools_dict:
                tool_output = tools_dict[name].invoke(args)
            else:
                tool_output = f"Error: La herramienta {name} no esta disponible."
                
            historial.append(ToolMessage(content=str(tool_output), tool_call_id=call_id))
            
        response = llm.invoke(historial)
        
    historial.append(response)
    return response.content
