FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY auth.py authenticate.py docs_tool.py gmail_tool.py server.py ./

ENV PYTHONUNBUFFERED=1

CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}
