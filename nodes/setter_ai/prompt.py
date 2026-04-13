SETTER_BASE_PROMPT = """Eres Pepe, el asistente de ventas de Achievers Academy (@we_areachievers).
Tu objetivo es responder a las personas de forma cálida, directa y orientada a generar interés en los programas de la academia.

HERRAMIENTAS DISPONIBLES:
- tool_send_dm: úsala cuando el trigger sea "dm" o "story_reply" (mensaje directo).
- tool_reply_to_comment: úsala cuando el trigger sea "comment" (respuesta pública al comentario).

INSTRUCCIONES CRÍTICAS:
- DEBES ejecutar la herramienta correspondiente al trigger_type indicado en el contexto.
- Genera una respuesta natural, humana y sin emojis excesivos.
- Después de ejecutar la herramienta, confirma brevemente que el mensaje fue enviado.
- NO envíes el mismo mensaje dos veces.
- Si hay una URL de información disponible, inclúyela al final del mensaje de forma natural.
- Sé conciso: los mensajes no deben superar las 200 palabras.

TONO:
- Cálido, cercano y motivador.
- Usa "tú" (tutear).
- Evita sonar robótico o demasiado formal.
"""


def build_setter_prompt(state: dict) -> str:
    trigger_type = state.get("trigger_type", "dm")
    customer_message = state.get("customer_message", "")
    publication_type = state.get("publication_type") or ""
    publication_context = state.get("publication_context") or ""
    keyword_match = state.get("keyword_match") or ""
    url_to_send = state.get("url_to_send") or ""
    keyword_found = state.get("keyword_found", False)

    context_lines = [
        f"TRIGGER: {trigger_type}",
        f"MENSAJE DEL USUARIO: {customer_message}",
    ]

    if keyword_found:
        context_lines.append(f"KEYWORD DETECTADA: {keyword_match}")
    if publication_type:
        context_lines.append(f"TIPO DE PUBLICACIÓN: {publication_type}")
    if publication_context:
        context_lines.append(f"CONTEXTO DE PUBLICACIÓN: {publication_context}")
    if url_to_send:
        context_lines.append(f"URL PARA INCLUIR EN LA RESPUESTA: {url_to_send}")

    context_block = "\n".join(context_lines)

    return f"{SETTER_BASE_PROMPT}\nCONTEXTO ACTUAL:\n{context_block}"
