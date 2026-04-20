import json

from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from nodes.normalize_input import SetterAIState
from nodes.setter_ai.prompt import build_qualification_prompt

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Número de turnos del usuario a partir del cual se califica
QUALIFY_AFTER_TURNS = 4


def _should_qualify(state: SetterAIState) -> bool:
    phase = state.get("conversation_phase", "open")
    if phase in ("pitch", "closed"):
        return False
    messages_count = state.get("messages_count") or 0
    return messages_count >= QUALIFY_AFTER_TURNS


def _build_conversation_summary(state: SetterAIState) -> str:
    messages = state.get("messages", [])
    lines = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            lines.append(f"Usuario: {msg.content}")
        elif isinstance(msg, AIMessage) and msg.content:
            lines.append(f"Setter: {msg.content}")
    return "\n".join(lines) if lines else state.get("customer_message", "")


def _determine_phase(score_virtual: int, score_inmersivo: int, messages_count: int, current_phase: str) -> str:
    if current_phase in ("pitch", "closed"):
        return current_phase
    best_score = max(score_virtual, score_inmersivo)
    if best_score >= 70:
        return "pitch"
    if best_score >= 40:
        return "qualify"
    return current_phase


def qualify_lead(state: SetterAIState) -> dict:
    messages_count = len([
        m for m in state.get("messages", [])
        if isinstance(m, HumanMessage)
    ])

    current_phase = state.get("conversation_phase") or "open"

    # Avanzar de open a qualify después del primer mensaje
    if current_phase == "open" and messages_count >= 1:
        current_phase = "qualify"

    if not _should_qualify({**state, "messages_count": messages_count, "conversation_phase": current_phase}):
        print(f"[QUALIFY_LEAD] phase={current_phase} turns={messages_count} — calificación aún no aplica")
        return {
            "conversation_phase": current_phase,
            "messages_count": messages_count,
        }

    summary = _build_conversation_summary(state)
    prompt = build_qualification_prompt(summary)

    try:
        response = _llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        # Extrae JSON si viene envuelto en markdown
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
    except Exception as e:
        print(f"[QUALIFY_LEAD] Error al calificar: {e}")
        return {
            "conversation_phase": current_phase,
            "messages_count": messages_count,
        }

    score_virtual = result.get("score_virtual", 0)
    score_inmersivo = result.get("score_inmersivo", 0)
    new_phase = _determine_phase(score_virtual, score_inmersivo, messages_count, current_phase)

    output = {
        "conversation_phase": new_phase,
        "messages_count": messages_count,
        "score_virtual": score_virtual,
        "score_inmersivo": score_inmersivo,
        "nivel_virtual": result.get("nivel_virtual"),
        "nivel_inmersivo": result.get("nivel_inmersivo"),
        "programa_recomendado": result.get("programa_recomendado"),
        "prioridad_comercial": result.get("prioridad_comercial"),
        "fit_financiero": result.get("fit_financiero"),
        "driver": result.get("driver"),
        "notas_calificacion": result.get("notas_calificacion"),
    }

    print(
        f"[QUALIFY_LEAD] turns={messages_count} phase={new_phase} "
        f"virtual={score_virtual} inmersivo={score_inmersivo} "
        f"programa={result.get('programa_recomendado')!r} "
        f"prioridad={result.get('prioridad_comercial')!r}"
    )
    return output
