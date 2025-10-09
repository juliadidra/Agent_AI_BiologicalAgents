FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/usr/local/bin:${PATH}"

WORKDIR /app

# --------------------
# Instalar dependências da API e WAHA
# --------------------
COPY requirements.txt requirements.txt
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Instalar WAHA diretamente da imagem oficial (opcional)
# Se você quiser rodar WAHA como pacote python, adapte conforme sua necessidade

# --------------------
# Copiar o código
# --------------------
COPY . .

# --------------------
# Instalar Nginx
# --------------------
RUN apt-get update && \
    apt-get install -y nginx && \
    rm -rf /var/lib/apt/lists/*

# Copiar configuração do Nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Expor apenas a porta do Nginx (80)
EXPOSE 80

# --------------------
# Comando de inicialização: WAHA + API + Nginx
# --------------------
CMD sh -c "\
    service nginx start && \
    python -m api & \
    python -m waha \
"
