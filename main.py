"""
FastAPI para configurar endpoints de respuesta al microservicio de setters
"""
#* Librerías para API
from fastapi import FastAPI, Request, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import PlainTextResponse, RedirectResponse
import os

from dotenv import load_dotenv

load_dotenv()

class AgenteInput(BaseModel):
    id_instagram: str = Field(...,example="1234567890", description="ID de Instagram del usuario/lead que envía el mensaje")
    id_publicacion: str | None = Field(None, example="1234567890", description="ID de la publicación (comentario) o null si es DM")
    customer_message: str = Field(..., description="Texto del mensaje del usuario")

# Parametros básicos y clases
app = FastAPI()
puerto = os.environ.get("PORT", 8080)

# Mismo valor que configuras en Meta Developers (Webhook > Verify Token)
INSTAGRAM_VERIFY_TOKEN = os.environ.get("INSTAGRAM_VERIFY_TOKEN", "")


def _process_instagram_webhook_payload(body: dict) -> None:
    from nodes.orchestration import call_setter_ai

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value") or {}
            if field == "messages":
                _instagram_handle_messages(value, call_setter_ai)
            elif field == "comments":
                _instagram_handle_comments(value, call_setter_ai)
            elif field == "story_insights":
                _instagram_handle_story_insights(value, call_setter_ai)


def _instagram_handle_messages(value: dict, call_setter_ai) -> None:
    for msg in value.get("messages", []):
        sender = msg.get("from") or {}
        text_obj = msg.get("text") or {}
        body_text = text_obj.get("body")
        ig_id = sender.get("id")
        if not body_text or ig_id is None:
            continue
        call_setter_ai(
            {
                "id_instagram": str(ig_id),
                "id_publicacion": None,
                "customer_message": body_text,
            }
        )


def _instagram_handle_comments(value: dict, call_setter_ai) -> None:
    from_user = value.get("from") or {}
    media = value.get("media") or {}
    ig_id = from_user.get("id")
    if ig_id is None:
        return
    mid = media.get("id")
    call_setter_ai(
        {
            "id_instagram": str(ig_id),
            "id_publicacion": str(mid) if mid is not None else None,
            "customer_message": value.get("text") or "",
        }
    )


def _instagram_handle_story_insights(value: dict, _call_setter_ai) -> None:
    # El payload de story_insights suele ser analíticas; ampliar si Meta envía respuestas a historias aquí
    if not value:
        return


# Configuración de CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



#* Definición de un endpoint
descripcion_path = 'Este endpoint recibe un mensaje de un cliente y devuelve una respuesta procesada por el setter.'
summary_path = 'Procesa un mensaje de cliente y devuelve una respuesta.'
endpoint_end = '/call-setter-ai'
@app.post(endpoint_end, summary=summary_path, description=descripcion_path)
async def setter_ai(input: AgenteInput):
    
    from nodes.orchestration import call_setter_ai
    
    input_dict = {
        "id_instagram": input.id_instagram,
        "id_publicacion": input.id_publicacion,
        "customer_message": input.customer_message,
    }
    response = call_setter_ai(input_dict)

    return response


@app.get("/webhook/instagram", response_class=PlainTextResponse)
async def instagram_verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    if not INSTAGRAM_VERIFY_TOKEN:
        return PlainTextResponse(
            content="Verification token not configured",
            status_code=503,
        )
    if (
        hub_mode == "subscribe"
        and hub_verify_token == INSTAGRAM_VERIFY_TOKEN
        and hub_challenge is not None
    ):
        return PlainTextResponse(content=hub_challenge)
    return PlainTextResponse(content="Token inválido", status_code=403)


@app.post("/webhook/instagram")
async def instagram_events_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    body = await request.json()
    background_tasks.add_task(_process_instagram_webhook_payload, body)
    return {"status": "ok"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Service is running"}

@app.get("/", response_class=RedirectResponse)
async def redirect_to_docs():
    return "/docs"



if __name__ == '__main__':

    import uvicorn
    
    uvicorn.run(app, host="127.0.0.1", port=int(puerto))
