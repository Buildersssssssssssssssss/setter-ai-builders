import os

from nodes.setter_ai.qualification_rules import SETTING_PHASES

SETTER_BASE_PROMPT = """Eres el setter de ventas de AI Builders (@ai__builders).
Tu objetivo es calificar, calentar y agendar llamadas calificadas.

HERRAMIENTAS DISPONIBLES:
- tool_send_dm: úsala cuando el trigger sea "dm" o "story_reply".
- tool_send_dm_from_comment: úsala cuando el trigger sea "comment" Y se detectó una keyword. Envía el DM usando el comment_id, sin restricción de ventana de 24h.
- tool_reply_to_comment: responde públicamente al comentario. Úsala siempre después de tool_send_dm_from_comment en el flujo de keyword.

INSTRUCCIONES CRÍTICAS:
- DEBES ejecutar la herramienta correspondiente al trigger_type para enviar tu respuesta.
- Después de ejecutar la herramienta, confirma brevemente que se envió.
- NO envíes el mismo mensaje dos veces.
- Si hay una URL disponible, inclúyela al final de forma natural.
- NUNCA uses emojis.
- Si el usuario tiene una queja, problema técnico, o necesita algo que no puedes resolver, usa tool_escalate_to_human indicando el motivo.

TONO Y ESTILO — MUY IMPORTANTE:
- Habla como un humano real, no como una IA.
- Tutear siempre, lenguaje informal y directo.
- Varía la estructura: a veces reacciona primero y luego pregunta, a veces solo pregunta, a veces comenta algo breve antes de continuar. No sigas siempre el mismo patrón.
- Las reacciones deben ser cortas y genuinas, no exageradas. Nada de "¡Increíble!", "¡Perfecto!", "¡Genial!". Mejor: "qué bueno", "tiene mucho sentido", "me parece interesante", "suena bien", "eso está bueno".
- Los mensajes pueden tener 1, 2 o 3 oraciones. No siempre 3. A veces una sola oración es suficiente.
- Usa saltos de línea cuando ayude a separar ideas, pero no siempre.
- Una sola pregunta por mensaje, nunca dos.
- Las preguntas deben sonar como parte de una conversación, no como un formulario.
- NUNCA empieces la respuesta con el nombre del usuario.
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

    # Caso especial: comment con keyword detectada
    if trigger_type == "comment" and keyword_found:
        user_first_name = (user_name or "").split()[0] if user_name else (user_username or "")
        dm_text = (
            f"Hola {user_first_name} 👋\n\n"
            f"Te damos la bienvenida a AI Builders 🐝👷🏽, una comunidad que convierte talento en impacto real por medio de AI.\n\n"
            f"Te envío la información de tu interés: {url_to_send}\n\n"
            f"Si tienes alguna duda, cuéntame por acá."
        ) if url_to_send else (
            f"Hola {user_first_name} 👋\n\n"
            f"Te damos la bienvenida a AI Builders 🐝👷🏽, una comunidad que convierte talento en impacto real por medio de AI.\n\n"
            f"Si tienes alguna duda, cuéntame por acá."
        )
        context_lines.append(
            f"ACCIÓN REQUERIDA — FLUJO ESPECIAL DE KEYWORD EN COMENTARIO:\n"
            f"1. Ejecuta tool_send_dm_from_comment con este mensaje exacto (no lo modifiques):\n{dm_text}\n"
            f"2. Luego ejecuta tool_reply_to_comment con un texto corto como: "
            f"\"Te envié la info por DM, cualquier duda me avisas\"\n"
            f"No hagas ninguna pregunta de calificación en esta interacción."
        )
    else:
        cal_url = os.environ.get("CAL_BOOKING_URL", "")
        pitch_instruction = (
            f"Estás en FASE PITCH: los calificadores están en check. "
            f"Propón agendar una llamada de forma natural y directa. "
            f"Incluye este link para que la persona agende directamente: {cal_url}"
        ) if cal_url else (
            "Estás en FASE PITCH: los calificadores están en check. Propón agendar una llamada de forma natural y directa."
        )

        phase_instruction = {
            "open": "Estás en FASE ABRIR: saluda de forma natural y cierra con una pregunta abierta para conocer al usuario.",
            "qualify": f"Estás en FASE CALIFICAR (turno {messages_count}): haz UNA pregunta de calificación natural. Máximo 5 preguntas en total antes del pitch.",
            "pitch": pitch_instruction,
            "closed": "La conversación está cerrada. Si el usuario escribe de nuevo, retoma con calidez.",
        }.get(conversation_phase, "")

        if phase_instruction:
            context_lines.append(f"INSTRUCCIÓN DE FASE: {phase_instruction}")

    context_block = "\n".join(context_lines)
    return f"{SETTER_BASE_PROMPT}\nCONTEXTO ACTUAL:\n{context_block}"


def build_qualification_prompt(conversation_summary: str) -> str:
    from nodes.setter_ai.qualification_rules import QUALIFICATION_RULES

    return f"""Eres un sistema de calificación de leads para AI Builders.
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
