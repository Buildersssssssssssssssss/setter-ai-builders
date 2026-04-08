"""
FastAPI para configurar endpoints de respuesta al microservicio de setters
"""
#* Librerías para API
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import RedirectResponse
import os

class AgenteInput(BaseModel):
    id_instagram: str = Field(...,example="1234567890", description="ID de Instagram del usuario/lead que envía el mensaje")
    id_publicacion: str | None = Field(None, example="1234567890", description="ID de la publicación (comentario) o null si es DM")
    customer_message: str = Field(..., description="Texto del mensaje del usuario")

# Parametros básicos y clases
app = FastAPI()
puerto = os.environ.get("PORT", 8080)


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


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Service is running"}

@app.get("/", response_class=RedirectResponse)
async def redirect_to_docs():
    return "/docs"



if __name__ == '__main__':

    import uvicorn
    
    uvicorn.run(app, host="127.0.0.1", port=int(puerto))
