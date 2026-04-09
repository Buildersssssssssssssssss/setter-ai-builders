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
GRAPH_URL = "https://graph.instagram.com/v25.0/me/messages"

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
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value", {})

            if field == "messages":
                sender_id = value.get("sender", {}).get("id")
                text = value.get("message", {}).get("text", "")
                print(f"[WEBHOOK] DM → sender_id={sender_id!r} text={text!r}")
                if sender_id and text:
                    background_tasks.add_task(
                        process_and_reply,
                        recipient_id=sender_id,
                        text=text,
                        trigger_type="dm",
                    )
                    tasks_scheduled += 1

            elif field == "comments":
                sender_id = value.get("from", {}).get("id")
                text = value.get("text", "")
                post_id = value.get("media", {}).get("id")
                comment_id = value.get("id")
                print(f"[WEBHOOK] Comentario → sender_id={sender_id!r} text={text!r}")
                if sender_id and text:
                    background_tasks.add_task(
                        process_and_reply,
                        recipient_id=sender_id,
                        text=text,
                        trigger_type="comment",
                        post_id=post_id,
                        comment_id=comment_id,
                    )
                    tasks_scheduled += 1

            else:
                print(f"[WEBHOOK] campo ignorado: {field!r}")

    print(f"[WEBHOOK] tasks_scheduled={tasks_scheduled}")
    return {"status": "ok"}


# ── Lógica principal: agente + envío ─────────────────────────────────────────

async def process_and_reply(
    recipient_id: str,
    text: str,
    trigger_type: str,
    post_id: str | None = None,
    comment_id: str | None = None,
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