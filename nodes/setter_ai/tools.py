from typing_extensions import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

import os

from utils.instagram import send_instagram_dm, send_instagram_dm_from_comment, reply_to_instagram_comment
from utils.whatsapp import send_human_escalation_alert

ESCALATION_MARKER = "__HUMAN_ESCALATION_REQUIRED__"


@tool
def tool_send_dm(
    message: str,
    state: Annotated[dict, InjectedState()],
) -> str:
    """Envía un mensaje directo (DM) de respuesta al usuario en Instagram."""
    recipient_id = state.get("id_instagram", "")
    if not recipient_id:
        return "Error: no hay id_instagram en el estado."
    username = state.get("user_username") or ""
    result = send_instagram_dm(recipient_id, message, username=username)
    if result.get("blocked"):
        return f"Envío bloqueado por whitelist (recipient_id={recipient_id})."
    if "error" in result:
        return f"Error al enviar DM: {result['error']}"
    return f"DM enviado correctamente a {recipient_id}."


@tool
def tool_reply_to_comment(
    message: str,
    state: Annotated[dict, InjectedState()],
) -> str:
    """Responde públicamente a un comentario en una publicación de Instagram."""
    comment_id = state.get("comment_id", "")
    if not comment_id:
        return "Error: no hay comment_id en el estado para responder."
    recipient_id = state.get("id_instagram", "")
    result = reply_to_instagram_comment(comment_id, message, recipient_id=recipient_id)
    if result.get("blocked"):
        return f"Envío bloqueado por whitelist (recipient_id={recipient_id})."
    if "error" in result:
        return f"Error al responder comentario: {result['error']}"
    return f"Comentario respondido correctamente (comment_id={comment_id})."


@tool
def tool_send_dm_from_comment(
    message: str,
    state: Annotated[dict, InjectedState()],
) -> str:
    """Envía un DM al usuario usando su comment_id como origen. Úsala cuando el trigger es 'comment' y se detectó una keyword, ya que no requiere ventana de 24h."""
    comment_id = state.get("comment_id", "")
    if not comment_id:
        return "Error: no hay comment_id en el estado."
    recipient_id = state.get("id_instagram", "")
    username = state.get("user_username") or ""
    result = send_instagram_dm_from_comment(comment_id, message, recipient_id=recipient_id, username=username)
    if result.get("blocked"):
        return f"Envío bloqueado por whitelist (recipient_id={recipient_id})."
    if "error" in result:
        return f"Error al enviar DM desde comentario: {result['error']}"
    return f"DM enviado correctamente desde comentario (comment_id={comment_id})."


@tool
def tool_escalate_to_human(
    reason: str,
    state: Annotated[dict, InjectedState()],
) -> str:
    """Escala la conversación a un humano cuando el usuario tiene una queja, problema técnico, o necesita atención que el setter no puede resolver. Incluye el motivo de la escalación."""
    sender_id = state.get("id_instagram", "")
    username = state.get("user_username") or sender_id or "desconocido"
    customer_message = state.get("customer_message", "")
    full_message = f"{reason}\n\nÚltimo mensaje del usuario: {customer_message}"

    reactivation_url = ""
    base_url = os.environ.get("APP_BASE_URL", "").rstrip("/")
    admin_token = os.environ.get("ADMIN_TOKEN", "")
    if base_url and admin_token and sender_id:
        reactivation_url = f"{base_url}/admin/unescalate/{sender_id}?token={admin_token}"

    send_human_escalation_alert(username=username, ig_message=full_message, reactivation_url=reactivation_url)
    print(f"[ESCALATION] Escalado a humano: @{username} — {reason}")
    return f"Conversación escalada a un humano. {ESCALATION_MARKER}"


tools_setter_ai = [tool_send_dm, tool_send_dm_from_comment, tool_reply_to_comment, tool_escalate_to_human]
