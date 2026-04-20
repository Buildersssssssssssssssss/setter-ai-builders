from nodes.normalize_input import SetterAIState
from utils.rag import search_knowledge


def retrieve_context(state: SetterAIState) -> dict:
    query = state.get("customer_message", "")
    if not query:
        return {"knowledge_context": ""}

    try:
        chunks = search_knowledge(query)
        context = "\n\n---\n\n".join(chunks) if chunks else ""
    except Exception as e:
        print(f"[RETRIEVE_CONTEXT] Error al buscar en Supabase: {e}")
        context = ""

    return {"knowledge_context": context}
