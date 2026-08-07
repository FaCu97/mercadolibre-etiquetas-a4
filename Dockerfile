FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Instalar Chromium + ChromeDriver para automatización Selenium
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    chromium \
    chromium-driver \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=America/Argentina/Buenos_Aires

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Directorios de datos y persistenia compartida entre contenedores
RUN mkdir -p comprobantes data


# Por defecto ejecuta el servicio de escucha de mails
CMD ["python", "services/mail_listener.py"]
