import os
from datetime import datetime, timezone

_supabase = None


def _get_client():
    global _supabase
    if _supabase is None:
        from supabase import create_client
        _supabase = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"],
        )
    return _supabase


def log_event(
    event_type: str,
    ig_id: str = "",
    ig_username: str = "",
    trigger_type: str = "",
    success: bool = True,
    error_code: int | None = None,
    response_time_ms: int | None = None,
) -> None:
    """
    Registra un evento del setter en la tabla setter_events.

    event_type: 'response' | 'pitch_link_sent' | 'escalation' | 'rate_limit'
    """
    row = {
        "event_type": event_type,
        "ig_id": ig_id or None,
        "ig_username": ig_username or None,
        "trigger_type": trigger_type or None,
        "success": success,
        "error_code": error_code,
        "response_time_ms": response_time_ms,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    row = {k: v for k, v in row.items() if v is not None}

    try:
        _get_client().table("setter_events").insert(row).execute()
    except Exception as e:
        print(f"[EVENTS] Error al registrar evento {event_type!r}: {e}")
