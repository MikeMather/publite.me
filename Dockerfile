FROM python:3.11.2 AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app


RUN python -m venv .venv
COPY requirements.txt ./
RUN .venv/bin/pip install -r requirements.txt
FROM python:3.11.2-slim
WORKDIR /app
COPY --from=builder /app/.venv .venv/
COPY . .
CMD [".venv/bin/python", "run.py"]
