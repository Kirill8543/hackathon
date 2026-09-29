FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Сертификаты Минцифры
RUN wget -q https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt \
        -O /usr/local/share/ca-certificates/russian_trusted_root_ca.crt \
 && wget -q https://gu-st.ru/content/lending/russian_trusted_sub_ca_pem.crt \
        -O /usr/local/share/ca-certificates/russian_trusted_sub_ca.crt \
 && update-ca-certificates

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
