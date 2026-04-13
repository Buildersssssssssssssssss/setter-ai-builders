"""
FastAPI para configurar endpoints de respuesta al microservicio de setters
"""
import asyncio
import json
import os
import random

from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse, HTMLResponse
from pydantic import BaseModel, Field

load_dotenv()

VERIFY_TOKEN = os.environ.get("INSTAGRAM_VERIFY_TOKEN", "")

# Modo test: solo procesa mensajes de sender_ids en la whitelist
# BOOL_TEST=true  →  activa el filtro
# TEST_WHITELIST=id1,id2,id3  →  IDs permitidos (comma-separated)
TEST_MODE = os.environ.get("BOOL_TEST", "false").strip().lower() in ("1", "true", "yes")
TEST_WHITELIST: set[str] = {
    sid.strip()
    for sid in os.environ.get("TEST_WHITELIST", "").split(",")
    if sid.strip()
}


def _sender_allowed(sender_id: str) -> bool:
    if not TEST_MODE:
        return True
    allowed = sender_id in TEST_WHITELIST
    if not allowed:
        print(f"[TEST] sender_id={sender_id!r} no está en la whitelist, ignorado")
    return allowed

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

        # ── Formato changes (webhooks de prueba del panel) ────────────────
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value", {})

            if field == "messages":
                sender_id = value.get("sender", {}).get("id")
                text = value.get("message", {}).get("text", "")
                print(f"[WEBHOOK] DM (changes) → sender_id={sender_id!r} text={text!r}")
                if sender_id and text and _sender_allowed(sender_id):
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
                if sender_id and text and _sender_allowed(sender_id):
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

        # ── Formato messaging (mensajes reales de Instagram) ──────────────
        for event in entry.get("messaging", []):
            msg = event.get("message", {})

            if msg.get("is_echo"):
                print(f"[WEBHOOK] Ignorando echo")
                continue

            if "message_edit" in event:
                print(f"[WEBHOOK] Ignorando message_edit")
                continue

            text = msg.get("text", "")
            if not text:
                print(f"[WEBHOOK] Ignorando mensaje sin texto: {list(msg.keys())}")
                continue

            sender_id = event.get("sender", {}).get("id")
            if not sender_id:
                continue

            story = msg.get("reply_to", {}).get("story", {})
            if story:
                event_trigger_type = "story_reply"
                story_id = story.get("id")
                story_link = story.get("url")
                print(f"[WEBHOOK] Story reply → sender_id={sender_id!r} story_id={story_id!r} text={text!r}")
            else:
                event_trigger_type = "dm"
                story_id = None
                story_link = None
                print(f"[WEBHOOK] DM (messaging) → sender_id={sender_id!r} text={text!r}")

            if _sender_allowed(sender_id):
                background_tasks.add_task(
                    process_and_reply,
                    recipient_id=sender_id,
                    text=text,
                    trigger_type=event_trigger_type,
                    story_id=story_id,
                    story_link=story_link,
                )
                tasks_scheduled += 1

    print(f"[WEBHOOK] tasks_scheduled={tasks_scheduled}")
    return {"status": "ok"}


# ── Lógica principal: agente (el envío ocurre dentro del grafo vía tools) ─────

async def process_and_reply(
    recipient_id: str,
    text: str,
    trigger_type: str,
    post_id: str | None = None,
    comment_id: str | None = None,
    story_id: str | None = None,
    story_link: str | None = None,
):
    from nodes.orchestration import call_setter_ai

    print(f"[REPLY] trigger={trigger_type} recipient={recipient_id!r} text={text!r}")
    await asyncio.sleep(random.uniform(3, 9))

    result = call_setter_ai({
        "id_instagram": recipient_id,
        "id_publicacion": post_id,
        "comment_id": comment_id,
        "story_id": story_id,
        "story_link": story_link,
        "customer_message": text,
        "trigger_type": trigger_type,
    })
    print(f"[REPLY] done — ai_response={result.get('message', '')[:80]!r}")

# --Politica de privacidad y terminos y condiciones ────────────────────────────

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    return """
    <html><body>
    <h1>Política de Privacidad</h1>
    <p>Esta aplicación procesa mensajes de Instagram únicamente para 
    responder automáticamente a usuarios que contactan la cuenta 
    @we_areachievers. No almacenamos datos personales de terceros.</p>
    </body></html>
    """


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