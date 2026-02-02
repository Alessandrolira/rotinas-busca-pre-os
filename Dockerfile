FROM python:3.11-slim

# Instala cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cria pasta de logs
RUN mkdir -p /logs

# Copia o cron
COPY crontab.txt /etc/cron.d/amil-cron
RUN sed -i 's/\r$//' /etc/cron.d/amil-cron && \
    chmod 0644 /etc/cron.d/amil-cron

# Garante que os scripts são executáveis
RUN chmod +x /app/run_precos.sh /app/run_rede.sh /app/run_precos_santa_helena.sh

CMD ["cron", "-f"]
