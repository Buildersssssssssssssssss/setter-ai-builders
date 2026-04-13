from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from nodes.check_publication import check_publication
from nodes.normalize_input import SetterAIState, normalize_input
from nodes.setter_ai.agent_setter_ai import (
    call_model_setter_ai,
    safe_tool_node_setter_ai,
    tools_condition_setter_ai,
)


def _route_after_normalize(state: SetterAIState) -> str:
    trigger_type = state.get("trigger_type", "dm")
    if trigger_type in ("comment", "story_reply"):
        return "check_publication"
    return "setter_ai"


grafo_setter = StateGraph(SetterAIState)

grafo_setter.add_node("normalize_input", normalize_input)
grafo_setter.add_node("check_publication", check_publication)
grafo_setter.add_node("setter_ai", call_model_setter_ai)
grafo_setter.add_node("tools", safe_tool_node_setter_ai)

grafo_setter.set_entry_point("normalize_input")

grafo_setter.add_conditional_edges(
    "normalize_input",
    _route_after_normalize,
    {"check_publication": "check_publication", "setter_ai": "setter_ai"},
)

grafo_setter.add_edge("check_publication", "setter_ai")

grafo_setter.add_conditional_edges(
    "setter_ai",
    tools_condition_setter_ai,
    {"tools": "tools", "__end__": END},
)

grafo_setter.add_edge("tools", "setter_ai")

memory = MemorySaver()
setter_agent = grafo_setter.compile(checkpointer=memory)


def call_setter_ai(input_data: dict) -> dict:
    thread_id = input_data.get("id_instagram", "default")
    config = {"configurable": {"thread_id": thread_id}}

    # El HumanMessage del turno actual se agrega aquí para que el reducer
    # lo acumule sobre el historial que guarda MemorySaver por thread_id.
    invoke_input = {
        **input_data,
        "messages": [HumanMessage(content=input_data.get("customer_message", ""))],
    }

    result = setter_agent.invoke(invoke_input, config=config)

    messages = result.get("messages", [])
    last_text = ""
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content and not getattr(msg, "tool_calls", None):
            last_text = msg.content
            break

    print(
        f"[ORCHESTRATION] "
        f"trigger={result.get('trigger_type')!r} "
        f"keyword_found={result.get('keyword_found')} "
        f"keyword_match={result.get('keyword_match')!r} "
        f"url_to_send={result.get('url_to_send')!r} "
        f"ai_response={last_text[:80]!r}"
    )
    return {"message": last_text}
