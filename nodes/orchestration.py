from langgraph.graph import StateGraph, END

from nodes.normalize_input import SetterAIState, normalize_input

grafo_setter = StateGraph(SetterAIState)

grafo_setter.add_node("normalize_input", normalize_input)

grafo_setter.set_entry_point("normalize_input")
grafo_setter.add_edge("normalize_input", END)

setter_agent = grafo_setter.compile()


def call_setter_ai(input_data: dict) -> dict:
    result = setter_agent.invoke(input_data)
    ai_response = result.get("ai_response") or ""
    print(f"[ORCHESTRATION] normalized_input={result.get('normalized_input')} ai_response={ai_response!r}")
    return {"message": ai_response}
