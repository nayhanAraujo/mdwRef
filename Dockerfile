FROM python:3.12-slim

# 1. Instala dependências essenciais
RUN apt-get update && apt-get install -y \
    wget \
    tar \
    gzip \
    libicu-dev \
    libtommath-dev \
    libboost-atomic1.74.0 \
    libboost-system1.74.0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Baixa e instala o Firebird 5.0.2 corretamente
RUN wget https://github.com/FirebirdSQL/firebird/releases/download/v5.0.2/FirebirdSS-5.0.2.1475-0.amd64.tar.gz -O /tmp/firebird.tar.gz && \
    tar -xzf /tmp/firebird.tar.gz -C /tmp && \
    cd /tmp/FirebirdSS-5.0.2.1475-0.amd64 && \
    ./install.sh -silent && \
    cd / && \
    rm -rf /tmp/FirebirdSS-5.0.2.1475-0.amd64 /tmp/firebird.tar.gz

# 3. Configurações pós-instalação
RUN echo "RemoteAccess = true" >> /opt/firebird/firebird.conf && \
    echo "WireCrypt = Enabled" >> /opt/firebird/firebird.conf && \
    echo "ServerMode = Super" >> /opt/firebird/firebird.conf && \
    ln -s /opt/firebird/bin/fbguard /usr/local/bin/fbguard && \
    ln -s /opt/firebird/bin/isql /usr/local/bin/isql-fb

# 4. Configuração do diretório da aplicação
WORKDIR /app

# 5. Prepara diretórios do banco de dados
RUN mkdir -p /app/data && \
    chown -R firebird:firebird /app/data && \
    chmod 775 /app/data

# 6. Copia o banco de dados
COPY ./BD/REFERENCIAS.FDB /app/data/
RUN chown firebird:firebird /app/data/REFERENCIAS.FDB && \
    chmod 644 /app/data/REFERENCIAS.FDB

# 7. Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 8. Copia o aplicativo
COPY . .

# 9. Comando de inicialização
CMD ["sh", "-c", "fbguard -daemon && gunicorn --bind 0.0.0.0:8080 --timeout 120 app:app"]