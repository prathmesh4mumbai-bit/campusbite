FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

# Install dependencies first so this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /code
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

# Secrets (DATABASE_URL, JWT_SECRET, OPENAI_API_KEY) are injected at runtime, never baked into the image.
# Single worker on purpose: the reminder job runs inside the app process.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
