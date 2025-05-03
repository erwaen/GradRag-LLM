FROM python:3.10-bullseye

# Evita que Python almacene archivos .pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y curl build-essential \
 && curl https://sh.rustup.rs -sSf | sh -s -- -y \
 && export PATH="$HOME/.cargo/bin:$PATH"


COPY ./requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . . 

 # CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
