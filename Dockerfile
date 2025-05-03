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
COPY ./BANCO_REFERENCIA/BD/REFERENCIAS.FDB /app/data/REFERENCIAS.FDB
RUN chmod 644 /app/data/REFERENCIAS.FDB

# Instala dependências Python (otimizado)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copia o resto do projeto
COPY . .

# Instala dependências Python
RUN pip install -r requirements.txt

# Define a porta e comando de execução
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "120", "app:app"]