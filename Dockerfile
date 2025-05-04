# Usa uma imagem base Python
FROM python:3.12-slim

# Instala dependências do sistema (necessário para Firebird e Mono)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    mono-complete \
    && rm -rf /var/lib/apt/lists/*

# Adiciona o repositório do Firebird 5.0 e instala o servidor
RUN wget -O - https://github.com/FirebirdSQL/firebird/releases/download/v5.0.2/Firebird-5.0.2.1613-0-linux-x64.tar.gz | tar -xz \
    && cd Firebird-5.0.0.1306-0-linux-amd64 \
    && ./install.sh -silent \
    && cd .. \
    && rm -rf Firebird-5.0.2.1613-0-linux-x64

# Configura o Firebird
RUN sed -i 's/RemoteBindAddress = .*/RemoteBindAddress = 0.0.0.0/' /opt/firebird/firebird.conf \
    && echo "ISC_PASSWORD=masterkey" > /opt/firebird/SYSDBA.password
# Configura o diretório da aplicação
WORKDIR /app

# Cria diretório para o Firebird e copia o banco de dados
RUN mkdir -p /app/data
COPY ./BD/REFERENCIAS.FDB /app/data/
RUN chmod 644 /app/data/REFERENCIAS.FDB

COPY ./ParseCSFile/ParseCSFile/bin/Debug/ParseCSFile.exe /app/ParseCSFile.exe
# Instala dependências Python (otimizado)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Copia o resto do projeto
COPY . .

RUN mkdir -p /app/sessions /app/uploads /app/data
# Define a porta e comando de execução
EXPOSE 8080
# Inicia o Firebird e o Gunicorn
CMD ["/bin/bash", "-c", "/opt/firebird/bin/fbguard -daemon && gunicorn --bind 0.0.0.0:8080 --timeout 120 app:app"]