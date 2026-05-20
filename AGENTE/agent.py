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
def consultar_e_sugerir_horas(fecha_preferida: str = None) -> str:
    """Consulta la disponibilidad en la agenda y sugiere hasta 3 horas libres.
    
    Args:
        fecha_preferida (str, optional): La fecha en la que el paciente quiere su cita en formato YYYY-MM-DD. 
                                          Si no se especifica, se sugerirán las primeras 3 horas de la semana.
    """
    try:
        sugerencias = calendar_manager.sugerir_horas(fecha_preferida)
        if not sugerencias:
            return "Lo siento, no quedan horas disponibles para esta semana en nuestro sistema."
        
        # Formatear la respuesta para el agente
        res = "Horas sugeridas disponibles:\n"
        for idx, sug in enumerate(sugerencias, 1):
            res += f"{idx}. Fecha: {sug['fecha']}, Hora: {sug['hora']}\n"
        return res
    except Exception as e:
        return f"Error al consultar disponibilidad: {e}"

@tool
def ejecutar_reserva_cita(fecha: str, hora: str, nombre_paciente: str) -> str:
    """Reserva un slot horario especifico en la agenda para un paciente.
    
    Args:
        fecha (str): Fecha seleccionada en formato YYYY-MM-DD.
        hora (str): Hora seleccionada en formato HH:MM.
        nombre_paciente (str): Nombre completo del paciente.
    """
    try:
        resultado = calendar_manager.reservar_hora(fecha, hora, nombre_paciente)
        return resultado
    except Exception as e:
        return f"Error al procesar la reserva: {e}"

tools = [consultar_e_sugerir_horas, ejecutar_reserva_cita]
tools_dict = {tool.name: tool for tool in tools}

# Definir el Prompt del Sistema con las directrices de Plaza Dent y el flujo de WhatsApp
SYSTEM_PROMPT_CONTENT = """Eres un asistente virtual amable y profesional de la Clínica Dental Plaza Dent, atendiendo a los pacientes que escriben por WhatsApp.
Tu objetivo es dar información de tratamientos y agendar citas de manera cálida y estructurada.

INFORMACIÓN DE LA CLÍNICA Y PROMOCIONES:
- Promoción de Limpieza: Limpieza dental profunda con ultrasonido + profilaxis + diagnóstico completo por solo $29.990 (precio normal: $45.000).
- Promoción de Prótesis Dentales: 20% de descuento en Prótesis Removibles y Prótesis Fijas (Metálica, Acrílica, Valplast) más evaluación gratuita con el especialista.
- Tratamientos Específicos: Ofrecemos Ortodoncia (brackets y alineadores invisibles), Endodoncia (tratamientos de conducto), Implantes Dentales, Blanqueamiento, Odontopediatría y Estética Dental.

PROTOCOLO DE CONVERSACIÓN (Sigue este orden de manera estricta):
1. BIENVENIDA (Primera Interacción):
   Da la bienvenida a la Clínica Dental Plaza Dent y pregunta exactamente:
   "¿Buscas más información sobre la promoción de Limpieza, de prótesis dentales o buscas algún tratamiento en específico?"
   NO agregues ni preguntes nada más en tu primer saludo.

2. RESPUESTA Y TRANSICIÓN (Segunda Interacción):
   - Responde con amabilidad sobre la consulta del paciente (Limpieza, Prótesis o Tratamiento específico) aportando los detalles del listado de arriba de forma clara.
   - Inmediatamente después de responder, haz la transición amable para el agendamiento diciendo exactamente:
     "Para poder ayudarte mejor, ¿para qué día te acomoda agendar una cita de evaluación?"

3. OFRECER HORAS DISPONIBLES:
   - Cuando el paciente indique el día (por ejemplo: "mañana", "el jueves", "el 25 de mayo", "el proximo lunes"), llama a la herramienta `consultar_e_sugerir_horas` pasando la fecha formateada en YYYY-MM-DD.
   - Nota importante sobre fechas: Considera que HOY es lunes 25 de mayo de 2026 (2026-05-25). Por lo tanto:
     * "lunes" es 2026-05-25
     * "martes" o "mañana" es 2026-05-26
     * "miércoles" es 2026-05-27
     * "jueves" es 2026-05-28
     * "viernes" es 2026-05-29
   - Presenta un listado ordenado de MÁXIMO 3 opciones de citas disponibles obtenidas de la herramienta (pueden ser del mismo día o de días diferentes de la semana).
   - Muestra la fecha y la hora con un formato muy amigable en español (ej. "Opción 1: Lunes 25 de Mayo a las 09:00 hrs").
   - Pregunta al paciente cuál de esas opciones prefiere.

4. CONFIRMACIÓN Y RESERVA:
   - Una vez que el paciente elija una de las opciones, pregúntale su nombre completo.
   - Cuando te proporcione su nombre, llama a la herramienta `ejecutar_reserva_cita` pasándole la fecha, la hora elegida y el nombre completo.
   - Confirma la reserva de manera muy amable y finaliza la conversación deseándole un excelente día.

REGLAS GENERALES:
- Habla siempre de forma empática y amable. ¡Deseamos que el paciente se sientan cómodo!
- Sé breve y estructurado en tus respuestas para que se lean bien en pantallas de móviles (WhatsApp).
- NUNCA inventes ni asumas horas disponibles. Consulta siempre con la herramienta `consultar_e_sugerir_horas`.
- Solo realiza la reserva usando la herramienta `ejecutar_reserva_cita` una vez que tengas la opción elegida y el nombre completo del paciente.
"""

# Instanciar ChatOpenAI usando la base de datos de GitHub Models
llm = ChatOpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("GITHUB_TOKEN"),
    model="gpt-4o-mini",  # Using gpt-4o-mini as a robust default for GitHub models
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
