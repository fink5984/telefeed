FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY telefeed.py /app/
# routes.yaml ו-.env יגיעו מבחוץ (bind)
RUN mkdir -p /app/data
VOLUME ["/app/data"]

CMD ["python", "/app/telefeed.py"]
