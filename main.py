"""
FastAPI para configurar endpoints de respuesta al microservicio de setters
"""
import asyncio
import json
import os
import random

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field

load_dotenv()

VERIFY_TOKEN = os.environ.get("INSTAGRAM_VERIFY_TOKEN", "")
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
# ID de la cuenta de Instagram de achievers (la que recibe y responde mensajes)
IG_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID", "")
GRAPH_BASE = "https://graph.instagram.com/v25.0"
GRAPH_URL = f"{GRAPH_BASE}/me/messages"

app = FastAPI()
puerto = os.environ.get("PORT", 8080)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgenteInput(BaseModel):
    id_instagram: str = Field(..., example="1234567890")
    id_publicacion: str | None = Field(None, example="1234567890")
    customer_message: str


# ── Endpoint manual (pruebas) ─────────────────────────────────────────────────

@app.post("/call-setter-ai")
async def setter_ai(input: AgenteInput):
    from nodes.orchestration import call_setter_ai
    return call_setter_ai({
        "id_instagram": input.id_instagram,
        "id_publicacion": input.id_publicacion,
        "customer_message": input.customer_message,
    })


# ── Verificación del webhook (GET) ────────────────────────────────────────────

@app.get("/webhook/instagram", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(content=hub_challenge)
    return PlainTextResponse(content="Token inválido", status_code=403)


# ── Recepción de eventos (POST) ───────────────────────────────────────────────

@app.post("/webhook/instagram")
async def instagram_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    print(f"[WEBHOOK] body: {json.dumps(body)}")

    tasks_scheduled = 0

    for entry in body.get("entry", []):
        entry_id = entry.get("id", "")

        # Solo procesar eventos de la cuenta receptora (achievers).
        # Meta envía el evento duplicado: una vez para el sender y otra para el recipient.
        # Si IG_ACCOUNT_ID está definido, ignoramos entradas que no sean de esa cuenta.
        if IG_ACCOUNT_ID and entry_id != IG_ACCOUNT_ID:
            print(f"[WEBHOOK] entry_id={entry_id!r} ignorado (no es IG_ACCOUNT_ID={IG_ACCOUNT_ID!r})")
            continue

        # DMs: formato messaging[] con clave message
        for event in entry.get("messaging", []):
            msg = event.get("message", {})
            message_edit = event.get("message_edit", {})

            # Mensaje nuevo directo
            if msg and not msg.get("is_echo"):
                sender_id = event.get("sender", {}).get("id")
                text = msg.get("text", "")
                print(f"[WEBHOOK] DM directo → sender_id={sender_id!r} text={text!r}")
                if sender_id and text:
                    background_tasks.add_task(
                        process_and_reply,
                        recipient_id=sender_id,
                        text=text,
                        trigger_type="dm",
                    )
                    tasks_scheduled += 1

            # Meta envía el envío inicial como message_edit con num_edit=0.
            # Necesitamos buscar el contenido con el mid.
            elif message_edit and message_edit.get("num_edit", -1) == 0:
                mid = message_edit.get("mid")
                sender_id = event.get("sender", {}).get("id")
                print(f"[WEBHOOK] message_edit num_edit=0 → mid={mid!r} sender_id={sender_id!r}")
                if mid and sender_id:
                    background_tasks.add_task(
                        process_message_edit,
                        mid=mid,
                        sender_id=sender_id,
                    )
                    tasks_scheduled += 1

            else:
                print(f"[WEBHOOK] messaging event ignorado: {json.dumps(event)}")

        # Comentarios y otros campos: entry[].changes[]
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value", {})
            print(f"[WEBHOOK] change field={field!r} value={json.dumps(value)}")

            if field == "messages":
                msg = value.get("message", {})
                if msg.get("is_echo"):
                    print(f"[WEBHOOK] messages is_echo, ignorado")
                    continue
                sender_id = value.get("sender", {}).get("id")
                text = msg.get("text", "")
                print(f"[WEBHOOK] messages → sender_id={sender_id!r} text={text!r}")
                if sender_id and text:
                    background_tasks.add_task(
                        process_and_reply,
                        recipient_id=sender_id,
                        text=text,
                        trigger_type="dm",
                    )
                    tasks_scheduled += 1

            elif field == "comments":
                recipient_id = value.get("from", {}).get("id")
                text = value.get("text", "")
                post_id = value.get("media", {}).get("id")
                print(f"[WEBHOOK] Comentario → recipient_id={recipient_id!r} text={text!r}")
                if recipient_id and text:
                    background_tasks.add_task(
                        process_and_reply,
                        recipient_id=recipient_id,
                        text=text,
                        trigger_type="comment",
                        post_id=post_id,
                    )
                    tasks_scheduled += 1

    print(f"[WEBHOOK] tasks_scheduled={tasks_scheduled}")
    return {"status": "ok"}


# ── Fetch mensaje por mid (para eventos message_edit num_edit=0) ──────────────

async def process_message_edit(mid: str, sender_id: str):
    print(f"[FETCH] Buscando mensaje mid={mid!r}")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{GRAPH_BASE}/{mid}",
            params={
                "fields": "id,message,from,created_time",
                "access_token": IG_ACCESS_TOKEN,
            },
        )
        data = response.json()
        print(f"[FETCH] response status={response.status_code} data={data}")

    if "error" in data:
        print(f"[FETCH] Error al buscar mensaje: {data['error']}")
        return

    text = data.get("message", "")
    from_id = data.get("from", {}).get("id", sender_id)

    # Si el mensaje viene de la propia cuenta (eco), ignorar
    if IG_ACCOUNT_ID and from_id == IG_ACCOUNT_ID:
        print(f"[FETCH] Mensaje propio ignorado (from_id={from_id!r})")
        return

    if text:
        await process_and_reply(recipient_id=from_id, text=text, trigger_type="dm")
    else:
        print(f"[FETCH] Sin texto en el mensaje mid={mid!r}")


# ── Lógica principal: agente + envío ─────────────────────────────────────────

async def process_and_reply(
    recipient_id: str,
    text: str,
    trigger_type: str,
    post_id: str | None = None,
):
    from nodes.orchestration import call_setter_ai

    print(f"[REPLY] trigger={trigger_type} recipient={recipient_id!r} text={text!r}")
    await asyncio.sleep(random.uniform(3, 9))

    result = call_setter_ai({
        "id_instagram": recipient_id,
        "id_publicacion": post_id,
        "customer_message": text,
    })
    print(f"[REPLY] call_setter_ai result={result}")

    reply_text = result.get("message") or result.get("text", "")
    if reply_text:
        print(f"[REPLY] Enviando DM a {recipient_id!r}: {reply_text!r}")
        await send_dm(recipient_id, reply_text)
    else:
        print(f"[REPLY] Sin texto para enviar. result={result}")


# ── Envío vía Graph API v25.0 ─────────────────────────────────────────────────

async def send_dm(recipient_id: str, message_text: str):
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text[:1000]},
        "messaging_type": "RESPONSE",
    }
    print(f"[GRAPH] POST {GRAPH_URL} → recipient={recipient_id!r} token_set={bool(IG_ACCESS_TOKEN)}")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            GRAPH_URL,
            json=payload,
            params={"access_token": IG_ACCESS_TOKEN},
        )
        data = response.json()
        print(f"[GRAPH] response status={response.status_code} data={data}")
        return data


# ── Utilidades ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Service is running"}

@app.get("/", response_class=RedirectResponse)
async def redirect_to_docs():
    return "/docs"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(puerto))
