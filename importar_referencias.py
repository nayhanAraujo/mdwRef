import json
from firebird.driver import connect, Error as FBError
from datetime import datetime
import os
import re

# Conexão com o Firebird
try:
    conn = connect(
        r"nayhan/3052:C:\Users\nayhan\Documents\PROJETOS AZURE\6- AZURE - REFERENCIAS\REFERENCIAS\BD\REFERENCIAS.FDB",
        user="SYSDBA",
        password="masterkey"
    )
    print("Conexão com o Firebird estabelecida com sucesso!")
except FBError as e:
    print(f"Erro na conexão com o Firebird: {e}")
    exit(1)

# Diretório base dos arquivos
BASE_DIR = r'C:\Users\nayhan\Documents\PROJETOS AZURE\6- AZURE - REFERENCIAS\REFERENCIAS\static\uploads\Cardiologia'

# Carrega o arquivo JSON
try:
    with open('Referencias.json', 'r', encoding='utf-8') as file:
        referencias = json.load(file)
except FileNotFoundError:
    print("Arquivo Referencias.json não encontrado!")
    conn.close()
    exit(1)

# Cria o cursor
cursor = conn.cursor()

# ID do usuário
CODUSUARIO = 4

# Obtém abreviações da tabela AUTORES
cursor.execute("SELECT ABREVIACAO, CODAUTOR FROM AUTORES WHERE ABREVIACAO IS NOT NULL")
abrev_autores = {row[0]: row[1] for row in cursor.fetchall()}

try:
    for ref in referencias:
        # Verifica se o título ou descrição contém alguma abreviação válida
        titulo = ref.get('Titulo', '').strip()
        descricao = ref.get('Descricao', '').strip()
        texto_completo = f"{titulo} {descricao}".lower()

        # Encontra abreviações presentes no texto
        abrev_encontradas = []
        for abrev in abrev_autores:
            # Usa regex para garantir que a abreviação seja uma palavra distinta
            if re.search(r'\b' + re.escape(abrev.lower()) + r'\b', texto_completo):
                abrev_encontradas.append(abrev)

        # Ignora a referência se nenhuma abreviação for encontrada
        if not abrev_encontradas:
            continue

        # Obtém ou insere a especialidade
        especialidade = ref.get('Especialidade', '').strip()
        cod_especialidade = None
        if especialidade:
            cursor.execute("""
                SELECT CODESPECIALIDADE FROM ESPECIALIDADE WHERE NOME = ?
            """, (especialidade,))
            result = cursor.fetchone()
            dthr_ult_modificacao = datetime.now()
            if result:
                cod_especialidade = result[0]
            else:
                cursor.execute("""
                    INSERT INTO ESPECIALIDADE (NOME, CODUSUARIO, DTHRULTMODIFICACAO)
                    VALUES (?, ?, ?)
                """, (especialidade, CODUSUARIO, dthr_ult_modificacao))
                
                # Buscar o ID da especialidade recém-inserida
                cursor.execute("""
                    SELECT CODESPECIALIDADE FROM ESPECIALIDADE WHERE NOME = ?
                """, (especialidade,))
                cod_especialidade = cursor.fetchone()[0]
        else:
            cod_especialidade = None  # Caso não haja especialidade

        # Insere na tabela REFERENCIA
        ano = ref.get('AnoPublicacao', None)
        dthr_ult_modificacao = datetime.now()

        cursor.execute("""
            INSERT INTO REFERENCIA (TITULO, ANO, DESCRICAO, CODUSUARIO, DTHRULTMODIFICACAO, CODESPECIALIDADE)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING CODREFERENCIA
        """, (titulo, ano, descricao, CODUSUARIO, dthr_ult_modificacao, cod_especialidade))
        
        cod_referencia = cursor.fetchone()[0]

        # Insere vínculos em REFERENCIA_AUTORES para abreviações encontradas
        for abrev in abrev_encontradas:
            cod_autor = abrev_autores[abrev]
            cursor.execute("""
                INSERT INTO REFERENCIA_AUTORES (CODREFERENCIA, CODAUTOR)
                VALUES (?, ?)
            """, (cod_referencia, cod_autor))

        # Insere na tabela ANEXOS
        arquivo = ref.get('Arquivo', '')
        if arquivo:
            nome_arquivo = os.path.basename(arquivo)
            caminho_completo = os.path.join(BASE_DIR, arquivo.lstrip('/static/uploads/').replace('/', '\\'))
            tipo_anexo = 'PDF' if nome_arquivo.lower().endswith('.pdf') else 'IMAGEM' if nome_arquivo.lower().endswith(('.jpg', '.jpeg', '.png')) else 'OUTRO'

            cursor.execute("""
                INSERT INTO ANEXOS (CODREFERENCIA, DESCRICAO, NOME, LINK, CAMINHO, CODUSUARIO, DTHRULTMODIFICACAO, TIPO_ANEXO)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cod_referencia, titulo, nome_arquivo, arquivo, caminho_completo, CODUSUARIO, dthr_ult_modificacao, tipo_anexo))

    # Confirma a transação
    conn.commit()
    print("Referências importadas com sucesso!")

except Exception as e:
    print(f"Erro durante a importação: {e}")
    conn.rollback()

finally:
    cursor.close()
    conn.close()
    print("Conexão com o banco fechada.")