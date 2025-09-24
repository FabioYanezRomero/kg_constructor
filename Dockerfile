FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    VLLM_URL=http://localhost:8000 \
    OUTPUT_DIR=/app/data/output

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY README.md ./
COPY Makefile ./
COPY LICENSE ./

RUN mkdir -p \"${OUTPUT_DIR}\"

ENTRYPOINT ["python", "-m", "kg_constructor"]
