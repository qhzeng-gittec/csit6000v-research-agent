FROM python:3.12-slim

RUN useradd --create-home --shell /bin/bash agent
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent ./agent
COPY tests ./tests
COPY scripts ./scripts
COPY splits ./splits
COPY web ./web
RUN mkdir -p /app/runs && chown -R agent:agent /app

USER agent
ENV PYTHONUNBUFFERED=1 CORPUS_DIR=/corpus
ENTRYPOINT ["python", "-m", "agent.run"]
