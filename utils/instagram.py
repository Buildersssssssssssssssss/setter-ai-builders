import os
import httpx

from utils.whatsapp import send_whatsapp_alert

GRAPH_BASE = "https://graph.instagram.com/v25.0"


def _token() -> str:
    return os.environ.get("IG_ACCESS_TOKEN", "")


def _recipient_allowed(recipient_id: str) -> bool:
    test_mode = os.environ.get("BOOL_TEST", "false").strip().lower() in ("1", "true", "yes")
    if not test_mode:
        return True
    whitelist = {
        sid.strip()
        for sid in os.environ.get("TEST_WHITELIST", "").split(",")
        if sid.strip()
    }
    allowed = recipient_id in whitelist
    if not allowed:
        print(f"[IG] recipient_id={recipient_id!r} no está en la whitelist, envío bloqueado")
    return allowed


def _alert_failed_dm(recipient_id: str, status_code: int, data: dict, username: str = "") -> None:
    error_msg = data.get("error", {}).get("message", "error desconocido")
    identifier = f"@{username}" if username else f"ID: {recipient_id}"
    msg = (
        f"*[AI Builders — Setter]*\n"
        f"No se pudo enviar DM en Instagram.\n\n"
        f"*Usuario:* {identifier}\n"
        f"*Error {status_code}:* {error_msg}\n\n"
        f"Requiere atención manual."
    )
    send_whatsapp_alert(msg)


def send_instagram_dm(recipient_id: str, text: str, username: str = "") -> dict:
    if not _recipient_allowed(recipient_id):
        return {"blocked": True, "reason": "test_whitelist"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text[:1000]},
        "messaging_type": "RESPONSE",
    }
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{GRAPH_BASE}/me/messages",
            json=payload,
            params={"access_token": _token()},
        )
    data = response.json()
    print(f"[IG] send_dm recipient={recipient_id!r} status={response.status_code} data={data}")
    if response.status_code != 200:
        _alert_failed_dm(recipient_id, response.status_code, data, username=username)
    return data


def send_instagram_dm_from_comment(comment_id: str, text: str, recipient_id: str = "", username: str = "") -> dict:
    """Envía un DM usando el comment_id como recipient, sin restricción de ventana de 24h."""
    if recipient_id and not _recipient_allowed(recipient_id):
        return {"blocked": True, "reason": "test_whitelist"}
    payload = {
        "recipient": {"comment_id": comment_id},
        "message": {"text": text[:1000]},
    }
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{GRAPH_BASE}/me/messages",
            json=payload,
            params={"access_token": _token()},
        )
    data = response.json()
    print(f"[IG] dm_from_comment comment_id={comment_id!r} status={response.status_code} data={data}")
    if response.status_code != 200:
        _alert_failed_dm(recipient_id or comment_id, response.status_code, data, username=username)
    return data


def reply_to_instagram_comment(comment_id: str, text: str, recipient_id: str = "") -> dict:
    if recipient_id and not _recipient_allowed(recipient_id):
        return {"blocked": True, "reason": "test_whitelist"}
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{GRAPH_BASE}/{comment_id}/replies",
            data={"message": text, "access_token": _token()},
        )
    data = response.json()
    print(f"[IG] reply_comment comment_id={comment_id!r} status={response.status_code} data={data}")
    return data
