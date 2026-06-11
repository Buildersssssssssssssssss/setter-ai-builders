import os
from datetime import datetime, timezone

from supabase import create_client

from nodes.normalize_input import SetterAIState

_supabase = None


def _get_client():
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"],
        )
    return _supabase


def save_lead(state: SetterAIState) -> dict:
    ig_id = state.get("id_instagram")
    if not ig_id:
        return {}

    human_escalated = state.get("human_escalated")

    row = {
        "ig_id": ig_id,
        "ig_username": state.get("user_username"),
        "ig_name": state.get("user_name"),
        "follower_count": state.get("user_follower_count"),
        "is_verified": state.get("user_is_verified", False),
        "fase_conversacion": state.get("conversation_phase"),
        "score_virtual": state.get("score_virtual"),
        "score_inmersivo": state.get("score_inmersivo"),
        "nivel_virtual": state.get("nivel_virtual"),
        "nivel_inmersivo": state.get("nivel_inmersivo"),
        "programa_recomendado": state.get("programa_recomendado"),
        "prioridad_comercial": state.get("prioridad_comercial"),
        "fit_financiero": state.get("fit_financiero"),
        "driver": state.get("driver"),
        "notas": state.get("notas_calificacion"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if human_escalated:
        row["escalated"] = True
        row["escalated_at"] = datetime.now(timezone.utc).isoformat()

    # Elimina claves con valor None para no sobrescribir datos existentes con null
    row = {k: v for k, v in row.items() if v is not None}

    try:
        client = _get_client()
        client.table("leads_setter").upsert(
            row,
            on_conflict="ig_id",
        ).execute()
        print(f"[SAVE_LEAD] upsert ok ig_user_id={ig_id}")
    except Exception as e:
        print(f"[SAVE_LEAD] Error al guardar lead: {e}")

    return {}
