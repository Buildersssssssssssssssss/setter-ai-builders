from langgraph.graph import StateGraph, END

from nodes.normalize_input import SetterAIState, normalize_input
from nodes.check_publication import check_publication


def _route_after_normalize(state: SetterAIState) -> str:
    trigger_type = state.get("trigger_type", "dm")
    if trigger_type in ("comment", "story_reply"):
        return "check_publication"
    return END


grafo_setter = StateGraph(SetterAIState)

grafo_setter.add_node("normalize_input", normalize_input)
grafo_setter.add_node("check_publication", check_publication)

grafo_setter.set_entry_point("normalize_input")
grafo_setter.add_conditional_edges(
    "normalize_input",
    _route_after_normalize,
    {"check_publication": "check_publication", END: END},
)
grafo_setter.add_edge("check_publication", END)

setter_agent = grafo_setter.compile()


def call_setter_ai(input_data: dict) -> dict:
    result = setter_agent.invoke(input_data)
    ai_response = result.get("ai_response") or ""
    print(
        f"[ORCHESTRATION] "
        f"trigger={result.get('trigger_type')!r} "
        f"keyword_found={result.get('keyword_found')} "
        f"keyword_match={result.get('keyword_match')!r} "
        f"url_to_send={result.get('url_to_send')!r} "
        f"ai_response={ai_response!r}"
    )
    return {"message": ai_response}
