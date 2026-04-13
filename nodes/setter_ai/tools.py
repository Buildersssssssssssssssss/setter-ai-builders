from typing_extensions import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from utils.instagram import send_instagram_dm, reply_to_instagram_comment


@tool
def tool_send_dm(
    message: str,
    state: Annotated[dict, InjectedState()],
) -> str:
    """Envía un mensaje directo (DM) de respuesta al usuario en Instagram."""
    recipient_id = state.get("id_instagram", "")
    if not recipient_id:
        return "Error: no hay id_instagram en el estado."
    result = send_instagram_dm(recipient_id, message)
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
    result = reply_to_instagram_comment(comment_id, message)
    if "error" in result:
        return f"Error al responder comentario: {result['error']}"
    return f"Comentario respondido correctamente (comment_id={comment_id})."


tools_setter_ai = [tool_send_dm, tool_reply_to_comment]
