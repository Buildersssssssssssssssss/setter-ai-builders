"""
Rate limiting y protecciones anti-ban para el setter de Instagram.
Todas las configuraciones se leen de variables de entorno para poder ajustarlas
sin redesplegar código.
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import redis

# ── Configuración desde .env ──────────────────────────────────────────────────

REDIS_URL = os.environ.get("REDIS_URL", "")

RATE_LIMIT_HOURLY = int(os.environ.get("RATE_LIMIT_HOURLY", "3"))
RATE_LIMIT_DAILY = int(os.environ.get("RATE_LIMIT_DAILY", "10"))
RATE_BLOCK_403_HOURS = int(os.environ.get("RATE_BLOCK_403_HOURS", "24"))
BUSINESS_HOURS_START = int(os.environ.get("BUSINESS_HOURS_START", "7"))
BUSINESS_HOURS_END = int(os.environ.get("BUSINESS_HOURS_END", "23"))
ESCALATION_TTL_HOURS = int(os.environ.get("ESCALATION_TTL_HOURS", "48"))

TZ_COLOMBIA = ZoneInfo("America/Bogota")

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis | None:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not REDIS_URL:
        print("[RATE] REDIS_URL no configurada, rate limiting desactivado")
        return None
    try:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=3)
        _redis_client.ping()
        print("[RATE] Conectado a Redis")
    except Exception as e:
        print(f"[RATE] No se pudo conectar a Redis: {e}. Rate limiting desactivado.")
        _redis_client = None
    return _redis_client


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_business_hours() -> bool:
    now = datetime.now(TZ_COLOMBIA)
    return BUSINESS_HOURS_START <= now.hour < BUSINESS_HOURS_END


def is_paused() -> bool:
    paused_env = os.environ.get("SETTER_PAUSED", "false").strip().lower()
    if paused_env in ("1", "true", "yes"):
        return True
    r = _get_redis()
    if r is None:
        return False
    try:
        return r.exists("setter:paused") == 1
    except Exception:
        return False


# ── API pública ───────────────────────────────────────────────────────────────

def can_respond(sender_id: str) -> tuple[bool, str]:
    """
    Retorna (True, "") si se puede responder, o (False, motivo) si no.
    """
    if is_paused():
        return False, "setter pausado globalmente"

    if not is_business_hours():
        return False, f"fuera de horario de negocio ({BUSINESS_HOURS_START}h–{BUSINESS_HOURS_END}h Colombia)"

    r = _get_redis()
    if r is None:
        return True, ""

    try:
        if r.exists(f"setter:blocked:{sender_id}"):
            ttl = r.ttl(f"setter:blocked:{sender_id}")
            return False, f"usuario bloqueado por 403 ({ttl}s restantes)"

        hourly_key = f"setter:hourly:{sender_id}"
        daily_key = f"setter:daily:{sender_id}"

        hourly = int(r.get(hourly_key) or 0)
        daily = int(r.get(daily_key) or 0)

        if hourly >= RATE_LIMIT_HOURLY:
            return False, f"límite horario alcanzado ({hourly}/{RATE_LIMIT_HOURLY})"

        if daily >= RATE_LIMIT_DAILY:
            return False, f"límite diario alcanzado ({daily}/{RATE_LIMIT_DAILY})"

    except Exception as e:
        print(f"[RATE] Error consultando Redis: {e}. Permitiendo respuesta.")

    return True, ""


def record_response(sender_id: str) -> None:
    """Incrementa los contadores después de una respuesta exitosa."""
    r = _get_redis()
    if r is None:
        return
    try:
        hourly_key = f"setter:hourly:{sender_id}"
        daily_key = f"setter:daily:{sender_id}"

        pipe = r.pipeline()
        pipe.incr(hourly_key)
        pipe.expire(hourly_key, 3600)
        pipe.incr(daily_key)
        pipe.expire(daily_key, 86400)
        pipe.execute()
    except Exception as e:
        print(f"[RATE] Error registrando respuesta en Redis: {e}")


def set_human_escalated(sender_id: str) -> None:
    """Marca al usuario como escalado a humano. El setter lo ignorará por ESCALATION_TTL_HOURS horas."""
    r = _get_redis()
    if r is None:
        print(f"[RATE] Redis no disponible, escalación no persistida para {sender_id!r}")
        return
    try:
        ttl_seconds = ESCALATION_TTL_HOURS * 3600
        r.setex(f"setter:escalated:{sender_id}", ttl_seconds, "1")
        print(f"[RATE] sender_id={sender_id!r} escalado a humano, TTL={ESCALATION_TTL_HOURS}h")
    except Exception as e:
        print(f"[RATE] Error guardando escalación en Redis: {e}")


def is_human_escalated(sender_id: str) -> bool:
    """Retorna True si el usuario está marcado como escalado a humano."""
    r = _get_redis()
    if r is None:
        return False
    try:
        return r.exists(f"setter:escalated:{sender_id}") == 1
    except Exception:
        return False


def clear_human_escalated(sender_id: str) -> None:
    """Desactiva manualmente la escalación para un usuario (para uso futuro desde endpoint)."""
    r = _get_redis()
    if r is None:
        return
    try:
        r.delete(f"setter:escalated:{sender_id}")
        print(f"[RATE] Escalación removida para sender_id={sender_id!r}")
    except Exception as e:
        print(f"[RATE] Error removiendo escalación: {e}")


def block_after_403(sender_id: str) -> None:
    """Bloquea a un usuario por RATE_BLOCK_403_HOURS horas después de un error 403."""
    r = _get_redis()
    if r is None:
        return
    try:
        ttl_seconds = RATE_BLOCK_403_HOURS * 3600
        r.setex(f"setter:blocked:{sender_id}", ttl_seconds, "403")
        print(f"[RATE] sender_id={sender_id!r} bloqueado por {RATE_BLOCK_403_HOURS}h tras 403")
    except Exception as e:
        print(f"[RATE] Error bloqueando usuario en Redis: {e}")
