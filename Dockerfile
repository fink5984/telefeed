FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY *.py /app/
COPY routes.yaml /app/
COPY templates/ /app/templates/
RUN mkdir -p /app/data /app/accounts

CMD ["python", "/app/web_ui.py"]
