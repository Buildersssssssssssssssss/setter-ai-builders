import os
import httpx

EVOLUTION_BASE = os.environ.get("EVOLUTION_API_URL", "").rstrip("/")
EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "")
ALERT_PHONE = os.environ.get("WA_ALERT_PHONE", "")


def send_whatsapp_alert(message: str, phone: str = "") -> dict:
    target = phone or ALERT_PHONE
    if not all([EVOLUTION_BASE, EVOLUTION_API_KEY, EVOLUTION_INSTANCE, target]):
        print("[WA] Configuración incompleta, alerta no enviada")
        return {"skipped": True}

    url = f"{EVOLUTION_BASE}/message/sendText/{EVOLUTION_INSTANCE}"
    payload = {
        "number": target,
        "text": message,
    }
    try:
        with httpx.Client(timeout=15) as client:
            response = client.post(
                url,
                json=payload,
                headers={"apikey": EVOLUTION_API_KEY},
            )
        data = response.json()
        print(f"[WA] alert sent to={target!r} status={response.status_code}")
        return data
    except Exception as e:
        print(f"[WA] Error enviando alerta: {e}")
        return {"error": str(e)}
