from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from nodes.check_publication import check_publication
from nodes.enrich_user import enrich_user
from nodes.normalize_input import SetterAIState, normalize_input
from nodes.qualify_lead import qualify_lead
from nodes.retrieve_context import retrieve_context
from nodes.save_lead import save_lead
from nodes.setter_ai.agent_setter_ai import (
    call_model_setter_ai,
    safe_tool_node_setter_ai,
    tools_condition_setter_ai,
)
from utils.rate_limiter import is_human_escalated


def _route_after_qualify(state: SetterAIState) -> str:
    sender_id = state.get("id_instagram", "")
    # Redis es la única fuente de verdad para la escalación
    if sender_id and is_human_escalated(sender_id):
        print(f"[ORCHESTRATION] sender_id={sender_id!r} escalado, saltando setter_ai.")
        return "save_lead"
    return "setter_ai"


def _route_after_normalize(state: SetterAIState) -> str:
    trigger_type = state.get("trigger_type", "dm")
    if trigger_type in ("comment", "story_reply"):
        return "check_publication"
    return "retrieve_context"


grafo_setter = StateGraph(SetterAIState)

grafo_setter.add_node("enrich_user", enrich_user)
grafo_setter.add_node("normalize_input", normalize_input)
grafo_setter.add_node("check_publication", check_publication)
grafo_setter.add_node("retrieve_context", retrieve_context)
grafo_setter.add_node("qualify_lead", qualify_lead)
grafo_setter.add_node("setter_ai", call_model_setter_ai)
grafo_setter.add_node("tools", safe_tool_node_setter_ai)
grafo_setter.add_node("save_lead", save_lead)

grafo_setter.set_entry_point("enrich_user")
grafo_setter.add_edge("enrich_user", "normalize_input")

grafo_setter.add_conditional_edges(
    "normalize_input",
    _route_after_normalize,
    {"check_publication": "check_publication", "retrieve_context": "retrieve_context"},
)

grafo_setter.add_edge("check_publication", "retrieve_context")
grafo_setter.add_edge("retrieve_context", "qualify_lead")
grafo_setter.add_conditional_edges(
    "qualify_lead",
    _route_after_qualify,
    {"setter_ai": "setter_ai", "save_lead": "save_lead"},
)

grafo_setter.add_conditional_edges(
    "setter_ai",
    tools_condition_setter_ai,
    {"tools": "tools", "__end__": "save_lead"},
)

grafo_setter.add_edge("tools", "setter_ai")
grafo_setter.add_edge("save_lead", END)

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
        f"phase={result.get('conversation_phase')!r} "
        f"score_virtual={result.get('score_virtual')} "
        f"score_inmersivo={result.get('score_inmersivo')} "
        f"programa={result.get('programa_recomendado')!r} "
        f"prioridad={result.get('prioridad_comercial')!r} "
        f"ai_response={last_text[:80]!r}"
    )
    return {"message": last_text}
