from typing import List, Optional
from typing_extensions import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class SetterAIState(TypedDict):
    # Input crudo
    id_instagram: str
    id_publicacion: Optional[str]
    comment_id: Optional[str]
    story_id: Optional[str]
    story_link: Optional[str]
    customer_message: str
    trigger_type: str               # "dm" | "comment" | "story_reply"

    # Historial de mensajes (reducer add_messages para persistencia con checkpointer)
    messages: Annotated[List[BaseMessage], add_messages]

    # Salida de normalize_input
    normalized_input: Optional[dict]

    # Salida de check_publication
    keyword_found: Optional[bool]
    keyword_match: Optional[str]
    publication_type: Optional[str]
    publication_context: Optional[str]
    url_to_send: Optional[str]

    # Salida del setter LLM
    ai_response: Optional[str]


def normalize_input(state: SetterAIState) -> dict:
    trigger_type = state.get("trigger_type") or (
        "comment" if state.get("id_publicacion") else "dm"
    )

    normalized = {
        "trigger_type": trigger_type,
        "ig_user_id": state["id_instagram"],
        "message": state["customer_message"],
    }

    if trigger_type == "comment":
        normalized["post_id"] = state.get("id_publicacion")
        normalized["comment_id"] = state.get("comment_id")

    elif trigger_type == "story_reply":
        normalized["story_id"] = state.get("story_id")
        if state.get("story_link"):
            normalized["story_link"] = state["story_link"]

    print(f"[NORMALIZE] trigger_type={trigger_type!r} normalized={normalized}")
    return {"normalized_input": normalized, "trigger_type": trigger_type}
