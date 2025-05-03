#!/bin/bash

# Esperar a que Qdrant esté listo (puedes afinar el timeout)

echo "Qdrant está listo. Iniciando FastAPI..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# exec fastapi dev main.py

