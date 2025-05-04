# Usa uma imagem base Python
FROM python:3.12-slim

# Instala dependências do sistema (necessário para o Firebird)
RUN apt-get update && apt-get install -y \
    wget \
    libfbclient2  \
    && rm -rf /var/lib/apt/lists/*



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
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "120", "app:app"]