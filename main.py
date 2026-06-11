"""
FastAPI para configurar endpoints de respuesta al microservicio de setters
"""
import asyncio
import json
import os
import random
import tempfile

from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Query, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse, HTMLResponse
from pydantic import BaseModel, Field

load_dotenv()

from utils.rate_limiter import (  # noqa: E402
    can_respond, record_response, clear_human_escalated, is_event_seen,
    buffer_message, pop_buffered_messages, should_alert_rate_limit,
    MESSAGE_BUFFER_WINDOW,
)
from utils.whatsapp import send_whatsapp_alert  # noqa: E402
from utils.supabase_events import log_event  # noqa: E402

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
IG_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID", "")

VERIFY_TOKEN = os.environ.get("INSTAGRAM_VERIFY_TOKEN", "")

SETTER_MIN_DELAY = float(os.environ.get("SETTER_MIN_DELAY", "15"))
SETTER_MAX_DELAY = float(os.environ.get("SETTER_MAX_DELAY", "45"))

# Modo test: solo procesa mensajes de sender_ids en la whitelist
# BOOL_TEST=true  →  activa el filtro
# TEST_WHITELIST=id1,id2,id3  →  IDs permitidos (comma-separated)
TEST_MODE = os.environ.get("BOOL_TEST", "false").strip().lower() in ("1", "true", "yes")
TEST_WHITELIST: set[str] = {
    sid.strip()
    for sid in os.environ.get("TEST_WHITELIST", "").split(",")
    if sid.strip()
}


def _rate_check(sender_id: str) -> tuple[bool, str]:
    return can_respond(sender_id)


def _alert_rate_limit(sender_id: str, username: str, reason: str, trigger_type: str = "") -> None:
    log_event("rate_limit", ig_id=sender_id, ig_username=username, trigger_type=trigger_type, success=False)
    if not should_alert_rate_limit(sender_id):
        return
    msg = (
        f"*[AI Builders — Setter]*\n"
        f"Se alcanzó el límite de respuestas automáticas.\n\n"
        f"*Usuario:* @{username or sender_id}\n"
        f"*Motivo:* {reason}\n\n"
        f"Continuar la conversación manualmente en Instagram."
    )
    send_whatsapp_alert(msg)


def _is_own_account(sender_id: str) -> bool:
    if IG_ACCOUNT_ID and sender_id == IG_ACCOUNT_ID:
        print(f"[SELF] Evento de la propia cuenta ignorado sender_id={sender_id!r}")
        return True
    return False


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


# ── Ingestión RAG ─────────────────────────────────────────────────────────────

@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    from utils.rag import ingest_file

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".pdf", ".md", ".markdown"):
        return {"error": f"Formato no soportado: {ext}. Usa PDF o MD."}

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        count = ingest_file(tmp_path, source_name=file.filename)
    finally:
        os.unlink(tmp_path)

    return {"status": "ok", "source": file.filename, "chunks_insertados": count}


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
                mid = value.get("message", {}).get("mid", "")
                print(f"[WEBHOOK] DM (changes) → sender_id={sender_id!r} text={text!r}")
                if sender_id and text and not _is_own_account(sender_id) and _sender_allowed(sender_id):
                    if mid and is_event_seen(mid):
                        print(f"[DEDUP] DM duplicado ignorado mid={mid!r}")
                    else:
                        allowed, reason = _rate_check(sender_id)
                        if allowed:
                            is_first = buffer_message(sender_id, text)
                            if is_first:
                                background_tasks.add_task(
                                    process_and_reply,
                                    recipient_id=sender_id,
                                    trigger_type="dm",
                                )
                                tasks_scheduled += 1
                        else:
                            print(f"[RATE] DM ignorado sender_id={sender_id!r}: {reason}")
                            _alert_rate_limit(sender_id, "", reason)

            elif field == "comments":
                sender_id = value.get("from", {}).get("id")
                text = value.get("text", "")
                post_id = value.get("media", {}).get("id")
                comment_id = value.get("id")
                print(f"[WEBHOOK] Comentario → sender_id={sender_id!r} text={text!r}")
                if sender_id and text and not _is_own_account(sender_id) and _sender_allowed(sender_id):
                    if comment_id and is_event_seen(comment_id):
                        print(f"[DEDUP] Comentario duplicado ignorado comment_id={comment_id!r}")
                    else:
                        allowed, reason = _rate_check(sender_id)
                        if allowed:
                            is_first = buffer_message(sender_id, text)
                            if is_first:
                                background_tasks.add_task(
                                    process_and_reply,
                                    recipient_id=sender_id,
                                    trigger_type="comment",
                                    post_id=post_id,
                                    comment_id=comment_id,
                                )
                                tasks_scheduled += 1
                        else:
                            print(f"[RATE] Comentario ignorado sender_id={sender_id!r}: {reason}")
                            _alert_rate_limit(sender_id, "", reason)

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

            recipient_account = event.get("recipient", {}).get("id", "")
            if IG_ACCOUNT_ID and recipient_account and recipient_account != IG_ACCOUNT_ID:
                print(f"[WEBHOOK] Evento ignorado — recipient={recipient_account!r} no es la cuenta business")
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

            mid = msg.get("mid", "")
            if not _is_own_account(sender_id) and _sender_allowed(sender_id):
                if mid and is_event_seen(mid):
                    print(f"[DEDUP] Mensaje duplicado ignorado mid={mid!r}")
                else:
                    allowed, reason = _rate_check(sender_id)
                    if allowed:
                        is_first = buffer_message(sender_id, text)
                        if is_first:
                            background_tasks.add_task(
                                process_and_reply,
                                recipient_id=sender_id,
                                trigger_type=event_trigger_type,
                                story_id=story_id,
                                story_link=story_link,
                            )
                            tasks_scheduled += 1
                    else:
                        print(f"[RATE] Mensaje ignorado sender_id={sender_id!r}: {reason}")
                        _alert_rate_limit(sender_id, "", reason)

    print(f"[WEBHOOK] tasks_scheduled={tasks_scheduled}")
    return {"status": "ok"}


# ── Lógica principal: agente (el envío ocurre dentro del grafo vía tools) ─────

async def process_and_reply(
    recipient_id: str,
    trigger_type: str,
    post_id: str | None = None,
    comment_id: str | None = None,
    story_id: str | None = None,
    story_link: str | None = None,
):
    import time
    from nodes.orchestration import call_setter_ai

    # Esperar la ventana de buffer para acumular mensajes consecutivos
    await asyncio.sleep(MESSAGE_BUFFER_WINDOW)

    messages = pop_buffered_messages(recipient_id)
    if not messages:
        print(f"[REPLY] Buffer vacío para recipient={recipient_id!r}, ignorando")
        return

    # Unir mensajes consecutivos en un solo texto con separador natural
    text = " | ".join(messages) if len(messages) > 1 else messages[0]
    print(f"[REPLY] trigger={trigger_type} recipient={recipient_id!r} mensajes={len(messages)} text={text!r}")

    # Delay humanizado adicional para parecer más natural
    base = random.uniform(SETTER_MIN_DELAY, SETTER_MAX_DELAY)
    jitter = random.gauss(0, 3)
    delay = max(SETTER_MIN_DELAY, base + jitter)
    print(f"[REPLY] delay={delay:.1f}s")
    await asyncio.sleep(delay)

    t0 = time.monotonic()
    try:
        result = call_setter_ai({
            "id_instagram": recipient_id,
            "id_publicacion": post_id,
            "comment_id": comment_id,
            "story_id": story_id,
            "story_link": story_link,
            "customer_message": text,
            "trigger_type": trigger_type,
        })
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        username = result.get("user_username", "")
        print(f"[REPLY] done — ai_response={result.get('message', '')[:80]!r} elapsed={elapsed_ms}ms")
        log_event(
            "response",
            ig_id=recipient_id,
            ig_username=username,
            trigger_type=trigger_type,
            success=True,
            response_time_ms=elapsed_ms,
        )
        record_response(recipient_id)
    except Exception as e:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        print(f"[REPLY] Error en call_setter_ai: {e}")
        log_event(
            "response",
            ig_id=recipient_id,
            trigger_type=trigger_type,
            success=False,
            response_time_ms=elapsed_ms,
        )

# ── Admin ─────────────────────────────────────────────────────────────────────

@app.get("/admin/unescalate/{sender_id}", response_class=HTMLResponse)
async def unescalate_user(sender_id: str, token: str = ""):
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        return HTMLResponse(content="<h2>No autorizado</h2>", status_code=403)
    clear_human_escalated(sender_id)
    print(f"[ADMIN] Escalación removida manualmente para sender_id={sender_id!r}")
    return HTMLResponse(content=f"""
    <html><body style="font-family:sans-serif;padding:2rem;">
    <h2>Setter reactivado</h2>
    <p>El setter volvió a estar activo para el usuario <strong>{sender_id}</strong>.</p>
    <p>El próximo mensaje de ese usuario será procesado normalmente.</p>
    </body></html>
    """)


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