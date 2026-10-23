# REI API. Build from the repository root (the image also needs database/):
#   docker build -f backend/Dockerfile .
FROM python:3.12-slim

# MALLOC_ARENA_MAX: feeds run on worker threads, and glibc gives each thread its
# own memory arena that keeps what a large run freed; on Railway the API grew to
# about 20 GB and was killed every few minutes (23 October 2026). Two arenas
# make later runs reuse that memory.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv/backend \
    MALLOC_ARENA_MAX=2

WORKDIR /srv

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY database database
COPY backend backend

RUN useradd --create-home rei && chown -R rei /srv
USER rei

EXPOSE 8000
# Keep-alive is longer than the web app's proxy keeps idle connections.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75"]
