"""
FastAPI para configurar endpoints de respuesta al microservicio de setters
"""
import asyncio
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

    for entry in body.get("entry", []):
        # DMs: Instagram usa entry[].messaging[]
        for event in entry.get("messaging", []):
            msg = event.get("message", {})
            if not msg or msg.get("is_echo"):
                continue
            sender_id = event.get("sender", {}).get("id")
            text = msg.get("text", "")
            if sender_id and text:
                background_tasks.add_task(
                    process_and_reply,
                    recipient_id=sender_id,
                    text=text,
                    trigger_type="dm",
                )

        # Comentarios: entry[].changes[]
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value", {})

            if field == "comments":
                recipient_id = value.get("from", {}).get("id")
                text = value.get("text", "")
                post_id = value.get("media", {}).get("id")
                if recipient_id and text:
                    background_tasks.add_task(
                        process_and_reply,
                        recipient_id=recipient_id,
                        text=text,
                        trigger_type="comment",
                        post_id=post_id,
                    )

    return {"status": "ok"}


# ── Lógica principal: agente + envío ─────────────────────────────────────────

async def process_and_reply(
    recipient_id: str,
    text: str,
    trigger_type: str,
    post_id: str | None = None,
):
    from nodes.orchestration import call_setter_ai

    await asyncio.sleep(random.uniform(3, 9))

    result = call_setter_ai({
        "id_instagram": recipient_id,
        "id_publicacion": post_id,
        "customer_message": text,
    })

    reply_text = result.get("message") or result.get("text", "")
    if reply_text:
        await send_dm(recipient_id, reply_text)


# ── Envío vía Graph API v25.0 ─────────────────────────────────────────────────

async def send_dm(recipient_id: str, message_text: str):
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text[:1000]},
        "messaging_type": "RESPONSE",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            GRAPH_URL,
            json=payload,
            params={"access_token": IG_ACCESS_TOKEN},
        )
        data = response.json()
        if "error" in data:
            print(f"Error Meta API: {data['error']}")
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
