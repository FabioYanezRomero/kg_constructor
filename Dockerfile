FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VLLM_URL=http://localhost:8000 \
    OUTPUT_DIR=/app/data/output

COPY pyproject.toml ./
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget git procps ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip

COPY kgb ./kgb
COPY README.md ./
COPY Makefile ./
COPY LICENSE ./

RUN pip install --no-cache-dir -e .

RUN mkdir -p "${OUTPUT_DIR}"

ENTRYPOINT ["kgb"]
