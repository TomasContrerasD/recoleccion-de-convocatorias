FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main_api.py config.py ./
COPY servicios ./servicios

ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn main_api:app --host 0.0.0.0 --port ${PORT:-8080}"]
