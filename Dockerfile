# FastAPI + Uvicorn (Railway inyecta PORT)
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Documentación; Railway asigna el puerto real vía PORT
EXPOSE 8080

# Railway define PORT; fallback 8080 para pruebas locales
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
