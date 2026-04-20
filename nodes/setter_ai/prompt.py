from nodes.setter_ai.qualification_rules import SETTING_PHASES

SETTER_BASE_PROMPT = """Eres Nico, el setter de ventas de Achievers Academy (@we_areachievers).
Tu objetivo es calificar, calentar y agendar llamadas calificadas.

HERRAMIENTAS DISPONIBLES:
- tool_send_dm: úsala cuando el trigger sea "dm" o "story_reply".
- tool_reply_to_comment: úsala cuando el trigger sea "comment".

INSTRUCCIONES CRÍTICAS:
- DEBES ejecutar la herramienta correspondiente al trigger_type para enviar tu respuesta.
- Después de ejecutar la herramienta, confirma brevemente que se envió.
- NO envíes el mismo mensaje dos veces.
- Si hay una URL disponible, inclúyela al final de forma natural.
- Mensajes máximo 200 palabras.
- Usa emojis con moderación, solo cuando aporten calidez.

TONO:
- Cálido, cercano y motivador.
- Tutear siempre.
- Natural, nunca robótico ni formal.
- Conversacional, no un interrogatorio.
"""

SETTER_BASE_PROMPT += "\n" + SETTING_PHASES


def build_setter_prompt(state: dict) -> str:
    trigger_type = state.get("trigger_type", "dm")
    customer_message = state.get("customer_message", "")
    publication_type = state.get("publication_type") or ""
    publication_context = state.get("publication_context") or ""
    keyword_match = state.get("keyword_match") or ""
    url_to_send = state.get("url_to_send") or ""
    keyword_found = state.get("keyword_found", False)
    knowledge_context = state.get("knowledge_context") or ""

    user_name = state.get("user_name") or ""
    user_username = state.get("user_username") or ""
    user_follower_count = state.get("user_follower_count")
    user_is_verified = state.get("user_is_verified", False)

    conversation_phase = state.get("conversation_phase") or "open"
    messages_count = state.get("messages_count") or 0

    context_lines = [
        f"TRIGGER: {trigger_type}",
        f"MENSAJE DEL USUARIO: {customer_message}",
        f"FASE ACTUAL DE LA CONVERSACIÓN: {conversation_phase}",
        f"TURNOS DEL USUARIO EN ESTA CONVERSACIÓN: {messages_count}",
    ]

    if user_name or user_username:
        user_lines = []
        if user_name:
            user_lines.append(f"Nombre: {user_name}")
        if user_username:
            user_lines.append(f"Username: @{user_username}")
        if user_follower_count is not None:
            user_lines.append(f"Seguidores: {user_follower_count:,}")
        if user_is_verified:
            user_lines.append("Cuenta verificada: sí")
        context_lines.append("PERFIL DEL USUARIO:\n" + "\n".join(user_lines))

    if knowledge_context:
        context_lines.append(
            f"BASE DE CONOCIMIENTO DEL PROGRAMA (usa esto para responder con precisión):\n{knowledge_context}"
        )
    if keyword_found:
        context_lines.append(f"KEYWORD DETECTADA: {keyword_match}")
    if publication_type:
        context_lines.append(f"TIPO DE PUBLICACIÓN: {publication_type}")
    if publication_context:
        context_lines.append(f"CONTEXTO DE PUBLICACIÓN: {publication_context}")
    if url_to_send:
        context_lines.append(f"URL PARA INCLUIR EN LA RESPUESTA: {url_to_send}")

    phase_instruction = {
        "open": "Estás en FASE ABRIR: saluda de forma natural y cierra con una pregunta abierta para conocer al usuario.",
        "qualify": f"Estás en FASE CALIFICAR (turno {messages_count}): haz UNA pregunta de calificación natural. Máximo 5 preguntas en total antes del pitch.",
        "pitch": "Estás en FASE PITCH: los calificadores están en check. Propón agendar una llamada de forma natural y directa.",
        "closed": "La conversación está cerrada. Si el usuario escribe de nuevo, retoma con calidez.",
    }.get(conversation_phase, "")

    if phase_instruction:
        context_lines.append(f"INSTRUCCIÓN DE FASE: {phase_instruction}")

    context_block = "\n".join(context_lines)
    return f"{SETTER_BASE_PROMPT}\nCONTEXTO ACTUAL:\n{context_block}"


def build_qualification_prompt(conversation_summary: str) -> str:
    from nodes.setter_ai.qualification_rules import QUALIFICATION_RULES

    return f"""Eres un sistema de calificación de leads para Achievers Academy.
Analiza la siguiente conversación y devuelve un JSON con la calificación del lead.

{QUALIFICATION_RULES}

CONVERSACIÓN A ANALIZAR:
{conversation_summary}

Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta:
{{
  "score_virtual": <int 0-100>,
  "score_inmersivo": <int 0-100>,
  "nivel_virtual": "<bajo|medio|alto|descalificado>",
  "nivel_inmersivo": "<bajo|medio|alto|descalificado>",
  "programa_recomendado": "<virtual|inmersivo|dual|nurture|descalificado>",
  "prioridad_comercial": "<alta|media|baja>",
  "fit_financiero": <int 0-15>,
  "driver": "<resumen breve del dolor o deseo detectado, máximo 100 chars>",
  "notas_calificacion": "<observaciones comerciales breves>"
}}
"""
