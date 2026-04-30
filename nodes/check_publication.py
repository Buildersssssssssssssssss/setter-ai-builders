import os
import time
import unicodedata
import httpx

from nodes.normalize_input import SetterAIState

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
SPREADSHEET_ID = os.environ.get("SHEETS_SPREADSHEET_ID", "")
TAB_NAME = os.environ.get("SHEETS_TAB_NAME", "DATA")
CACHE_TTL_SECONDS = int(os.environ.get("SHEETS_CACHE_TTL", "300"))  # 5 min default

_sheets_cache: list[dict] | None = None
_cache_timestamp: float = 0.0


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _fetch_sheet_rows() -> list[dict]:
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/"
        f"{SPREADSHEET_ID}/values/{TAB_NAME}!A:E"
    )
    with httpx.Client(timeout=15) as client:
        response = client.get(url, params={"key": GOOGLE_API_KEY})
        response.raise_for_status()
        data = response.json()

    rows = data.get("values", [])
    if not rows:
        return []

    headers = [h.strip() for h in rows[0]]
    return [dict(zip(headers, row)) for row in rows[1:] if row]


def _get_sheet_data() -> list[dict]:
    global _sheets_cache, _cache_timestamp
    now = time.monotonic()
    if _sheets_cache is None or (now - _cache_timestamp) > CACHE_TTL_SECONDS:
        print(f"[SHEETS] Recargando datos del sheet...")
        _sheets_cache = _fetch_sheet_rows()
        _cache_timestamp = now
        print(f"[SHEETS] {len(_sheets_cache)} publicaciones cargadas")
    return _sheets_cache


def _keyword_matches(message: str, keywords_raw: str) -> str | None:
    """
    Retorna la primera keyword que coincide en el mensaje, o None.
    Soporta múltiples keywords separadas por coma.
    La comparación es case-insensitive y sin tildes.
    """
    norm_message = _normalize_text(message)
    for kw in keywords_raw.split(","):
        kw_clean = _normalize_text(kw)
        if kw_clean and kw_clean in norm_message:
            return kw.strip()
    return None


def check_publication(state: SetterAIState) -> dict:
    trigger_type = state.get("trigger_type", "")
    normalized = state.get("normalized_input") or {}

    pub_id = normalized.get("post_id") or normalized.get("story_id")

    print(f"[CHECK_PUB] trigger_type={trigger_type!r} pub_id={pub_id!r}")

    if not pub_id:
        print(f"[CHECK_PUB] Sin pub_id, saltando lookup")
        return {"keyword_found": False}

    try:
        rows = _get_sheet_data()
    except Exception as e:
        print(f"[CHECK_PUB] Error al leer sheet: {e}")
        return {"keyword_found": False}

    pub_row = next(
        (r for r in rows if r.get("ID", "").strip() == str(pub_id)),
        None,
    )

    if not pub_row:
        print(f"[CHECK_PUB] pub_id={pub_id!r} no encontrado en sheet")
        return {"keyword_found": False}

    message = state.get("customer_message", "")
    keywords_raw = pub_row.get("Keywords", "")
    matched_keyword = _keyword_matches(message, keywords_raw)

    result = {
        "keyword_found": matched_keyword is not None,
        "keyword_match": matched_keyword,
        "publication_type": pub_row.get("Type"),
        "publication_context": pub_row.get("Context"),
        "url_to_send": pub_row.get("URL_info_to_send") if matched_keyword else None,
    }

    print(f"[CHECK_PUB] result={result}")
    return result
