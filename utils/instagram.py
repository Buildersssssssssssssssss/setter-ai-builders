import os
import httpx

GRAPH_BASE = "https://graph.instagram.com/v25.0"


def _token() -> str:
    return os.environ.get("IG_ACCESS_TOKEN", "")


def send_instagram_dm(recipient_id: str, text: str) -> dict:
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
    return data


def reply_to_instagram_comment(comment_id: str, text: str) -> dict:
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{GRAPH_BASE}/{comment_id}/replies",
            data={"message": text, "access_token": _token()},
        )
    data = response.json()
    print(f"[IG] reply_comment comment_id={comment_id!r} status={response.status_code} data={data}")
    return data
