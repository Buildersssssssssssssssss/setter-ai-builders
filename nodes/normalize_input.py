from typing import Optional
from typing_extensions import TypedDict


class SetterAIState(TypedDict):
    id_instagram: str
    id_publicacion: Optional[str]
    comment_id: Optional[str]
    customer_message: str
    trigger_type: str           # "dm" | "comment"
    normalized_input: Optional[dict]
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

    print(f"[NORMALIZE] trigger_type={trigger_type!r} normalized={normalized}")
    return {"normalized_input": normalized, "trigger_type": trigger_type}
