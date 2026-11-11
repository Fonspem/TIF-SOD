# API de metadatos del TIF. La levanta monitoring/compose.yaml con red host, en el puerto 8000.
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
USER 65534:65534
ENV PORT=8000 PYTHONUNBUFFERED=1
CMD ["python", "app.py"]
