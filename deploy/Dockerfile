# UND — All In One · container image
# Build from the repo root:  docker build -f deploy/Dockerfile -t und-bot .
# Run:                       docker run -d --name und --env-file bot/.env -p 8000:8000 und-bot
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=UTC

# ffmpeg = music, libsndfile/espeak not needed (pyttsx3 is not used at runtime)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY bot/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY bot/ ./

# SQLite databases live next to the code; keep them on a volume:
VOLUME ["/app/db", "/app/jsondb"]

EXPOSE 8000
CMD ["python", "UND.py"]
