# The Memory Palace — Hugging Face Spaces (Docker SDK)
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

# HF Spaces run the container as uid 1000. Create that user and make the app
# directory writable so Cognee can persist .cognee_system at runtime.
RUN useradd -m -u 1000 user
WORKDIR /app
COPY . /app
RUN chown -R user:user /app

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860

RUN pip install --no-cache-dir --user -e .

EXPOSE 7860

# Ingest the world graph on first boot (if missing), then serve.
CMD ["bash", "-lc", "python scripts/ensure_graph.py && exec python -m uvicorn api.app:app --host 0.0.0.0 --port ${PORT:-7860}"]
