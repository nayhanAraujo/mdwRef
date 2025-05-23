# Usa uma imagem base Python
FROM python:3.12-slim

# Instala dependências do sistema (necessário para Firebird e Mono)
RUN apt-get update && apt-get install -y \
    wget \
    tar \
    gnupg \
    net-tools \
    libtommath-dev \
    libicu-dev \
    libboost-atomic1.74.0 \
    libboost-system1.74.0 \
    libboost-filesystem1.74.0 \
    libboost-regex1.74.0 \
    mono-complete \
    && rm -rf /var/lib/apt/lists/*

# Adiciona o repositório do Firebird 5.0 e instala o servidor
RUN wget -O - https://github.com/FirebirdSQL/firebird/releases/download/v5.0.2/Firebird-5.0.2.1613-0-linux-x64.tar.gz | tar -xz \
    && cd Firebird-5.0.2.1613-0-linux-x64 \
    && ./install.sh -silent \
    && cd .. \
    && rm -rf Firebird-5.0.2.1613-0-linux-x64

# Configura o Firebird

# Configura o Firebird
RUN sed -i 's/RemoteBindAddress = .*/RemoteBindAddress = 0.0.0.0/' /opt/firebird/firebird.conf \
    && /opt/firebird/bin/gsec -user SYSDBA -password masterkey -modify SYSDBA -pw masterkey \
    && echo "ISC_PASSWORD=masterkey" > /opt/firebird/SYSDBA.password \
    && chmod 600 /opt/firebird/SYSDBA.password \
    && chown firebird:firebird /opt/firebird/SYSDBA.password
# Configura o diretório da aplicação
WORKDIR /app

# Cria diretório para o Firebird e copia o banco de dados
RUN mkdir -p /app/data \
    && chown firebird:firebird /app/data
COPY ./BD/REFERENCIAS.FDB /app/data/
RUN chmod 664 /app/data/REFERENCIAS.FDB \
    && chown firebird:firebird /app/data/REFERENCIAS.FDB

COPY ./ParseCSFile/ParseCSFile/bin/Debug/ParseCSFile.exe /app/ParseCSFile.exe
# Instala dependências Python (otimizado)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Copia o resto do projeto
COPY . .
# Cria diretórios necessários
RUN mkdir -p /app/sessions /app/uploads /app/data \
    && chown firebird:firebird /app/data \
    && chmod 777 /app/sessions  # Permissões amplas para evitar problemas
# Define a porta e comando de execução
EXPOSE 8080
# Inicia o Firebird e o Gunicorn
CMD ["/bin/bash", "-c", "echo 'Iniciando Firebird...' >> /opt/firebird/firebird.log && /opt/firebird/bin/fbguard -pidfile /opt/firebird/firebird.pid -daemon || { echo 'Falha ao iniciar Firebird via fbguard' >> /opt/firebird/firebird.log; exit 1; } && sleep 30 && /opt/firebird/bin/isql -u SYSDBA -p masterkey 127.0.0.1/3050:/app/data/REFERENCIAS.FDB -z >> /opt/firebird/firebird.log 2>&1 || echo 'Erro ao conectar ao Firebird via isql' >> /opt/firebird/firebird.log && (netstat -tuln | grep 3050 || ss -tuln | grep 3050 || echo 'Firebird não está ouvindo na porta 3050' >> /opt/firebird/firebird.log) && gunicorn --bind 0.0.0.0:8080 --timeout 120 app:app"]