FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# uv pip compile pyproject.toml -o requirements.txt
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# uvicorn app.main:app --host 0.0.0.0 --port 8001 --loop uvloop --http httptools --log-level warning
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--loop", "uvloop", "--http", "httptools", "--log-level", "warning"]
