import os
import time
import unicodedata

from nodes.normalize_input import SetterAIState

CACHE_TTL_SECONDS = int(os.environ.get("PUBLICATIONS_CACHE_TTL", "300"))  # 5 min default

_publications_cache: list[dict] | None = None
_cache_timestamp: float = 0.0

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


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _fetch_publications() -> list[dict]:
    response = (
        _get_client()
        .table("ig_publications")
        .select("ig_media_id, media_type, description, context, keywords, url_to_send, setter_active")
        .eq("setter_active", True)
        .execute()
    )
    return response.data or []


def _get_publications() -> list[dict]:
    global _publications_cache, _cache_timestamp
    now = time.monotonic()
    if _publications_cache is None or (now - _cache_timestamp) > CACHE_TTL_SECONDS:
        print("[CHECK_PUB] Recargando publicaciones desde Supabase...")
        _publications_cache = _fetch_publications()
        _cache_timestamp = now
        print(f"[CHECK_PUB] {len(_publications_cache)} publicaciones activas cargadas")
    return _publications_cache


def _keyword_matches(message: str, keywords: list[str]) -> str | None:
    """
    Retorna la primera keyword que coincide en el mensaje, o None.
    La comparación es case-insensitive y sin tildes.
    keywords es un array de strings (tipo text[] en Supabase).
    """
    norm_message = _normalize_text(message)
    for kw in keywords:
        if not kw:
            continue
        if _normalize_text(kw) in norm_message:
            return kw
    return None


def check_publication(state: SetterAIState) -> dict:
    trigger_type = state.get("trigger_type", "")
    normalized = state.get("normalized_input") or {}

    pub_id = normalized.get("post_id") or normalized.get("story_id")

    print(f"[CHECK_PUB] trigger_type={trigger_type!r} pub_id={pub_id!r}")

    if not pub_id:
        print("[CHECK_PUB] Sin pub_id, saltando lookup")
        return {"keyword_found": False}

    try:
        publications = _get_publications()
    except Exception as e:
        print(f"[CHECK_PUB] Error al leer publicaciones de Supabase: {e}")
        return {"keyword_found": False}

    pub = next(
        (p for p in publications if p.get("ig_media_id") == str(pub_id)),
        None,
    )

    if not pub:
        print(f"[CHECK_PUB] pub_id={pub_id!r} no encontrado en ig_publications")
        return {"keyword_found": False}

    message = state.get("customer_message", "")
    keywords = pub.get("keywords") or []
    matched_keyword = _keyword_matches(message, keywords)

    result = {
        "keyword_found": matched_keyword is not None,
        "keyword_match": matched_keyword,
        "publication_type": pub.get("media_type"),
        "publication_context": pub.get("context") or pub.get("description"),
        "url_to_send": pub.get("url_to_send") if matched_keyword else None,
    }

    print(f"[CHECK_PUB] result={result}")
    return result
