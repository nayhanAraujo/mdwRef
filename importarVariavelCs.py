import re
import firebird.driver as fbd
from firebird.driver import connect, Error as FBError

# Função para conectar ao banco Firebird e obter siglas e variáveis existentes
def get_existing_variables(db_host, db_path, db_user, db_password):
    existing_siglas = set()
    existing_variaveis = set()
    try:
        con = connect(
            r"nayhan/3052:C:\Users\nayhan\Documents\PROJETOS AZURE\6- AZURE - REFERENCIAS\REFERENCIAS\BD\REFERENCIAS.FDB",
            user="SYSDBA",
            password="masterkey"
        )
        print("Conexão com o Firebird estabelecida com sucesso!")
        cur = con.cursor()
        cur.execute("SELECT SIGLA, VARIAVEL FROM VARIAVEIS")
        for row in cur.fetchall():
            existing_siglas.add(row[0])
            existing_variaveis.add(row[1])
        cur.close()
        con.close()
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return set(), set()
    return existing_siglas, existing_variaveis

# Função para extrair variáveis do arquivo .cs que são TextBox
def extract_variables_from_cs(file_path):
    variables = set()
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        matches = re.findall(r'this\.(VR_\w+)\s*=\s*new\s*System\.Windows\.Forms\.TextBox\s*\(\s*\)\s*;', content)
        for match in matches:
            variables.add(match)
    return variables

# Função para gerar descrição em português
def generate_description(var_name):
    name = var_name.replace('VR_', '').replace('_', ' ')
    mapping = {
        'AO': 'Aorta',
        'AE': 'Átrio Esquerdo',
        'VD': 'Ventrículo Direito',
        'VE': 'Ventrículo Esquerdo',
        'SC': 'Indexado',
        'A4C': '4 Câmaras',
        'A2C': '2 Câmaras',
        'DIASTOLE': 'Diastólica',
        'SISTOLE': 'Sistólica',
        'FAC': 'Fração de Área',
        'COMP': 'Comprimento',
        'MVE': 'Massa do Ventrículo Esquerdo',
        'ERP': 'Espessura Relativa Paredes',
        'PPVE': 'Parede Posterior VE',
        'SEPTO': 'Septo',
        'PSAP': 'Pressão Sistólica Artéria Pulmonar',
        'VCI': 'Veia Cava Inferior',
        'INDICE': 'Índice',
        'REL': 'Relação',
        'LINHA': 'Linha',
        'FETEICHHOLZ': 'Fração Ejeção Teichholz',
        'FESIMPSON': 'Fração Ejeção Simpson',
        'SUPCORP': 'Superfície Corporal',
        'PESOPACIENTE': 'Peso do Paciente',
        'ALTURAPACIENTE': 'Altura do Paciente',
        'IMC': 'Índice de Massa Corporal',
        'DESCRICAOIMC': 'Descrição do IMC',
        'SGL': 'Strain Global Longitudinal',
        'DPDTVE': 'dP/dT do Ventrículo Esquerdo',
        'SLINHA': 'Strain Linha',
        'MAPS': 'MAPSE',
        'VAD': 'Volume Átrio Direito',
        'BT': 'Base-Topo',
        'EVD': 'Espessura Ventrículo Direito',
        'VATL': 'Velocidade Átrio Lateral',
        'GLSVD': 'Strain Global Ventrículo Direito',
        'FWSVD': 'Strain Livre Ventrículo Direito',
        'DSATL': 'Desaceleração Átrio Lateral',
        'DPDT': 'dP/dT',
        'VEL': 'Velocidade',
        'REG': 'Regurgitação',
        'PPICO': 'Pressão de Pico',
        'AD': 'Átrio Direito',
        'DT': 'Deceleração',
        'SV': 'Seio Valsalva',
        'JUNCAO': 'Junção',
        'ASC': 'Ascendente',
        'PROX': 'Proximal',
        'ARCOAO': 'Arco Aórtico',
        'VSVE': 'Volume Sistólico Ventrículo Esquerdo',
        'VEDI': 'Ventrículo Esquerdo Diastólico Indexado',
        'VDF': 'Volume Diastólico Final',
        'VSF': 'Volume Sistólico Final',
        'PEC': 'Percentual Encurtamento',
        'PAREDES': 'Paredes',
        'REPOUSO': 'Repouso',
        'STRESS': 'Estresse'
    }
    words = name.split()
    description = ' '.join(mapping.get(word.upper(), word.capitalize()) for word in words)
    return description

# Função para gerar sigla
def generate_sigla(var_name):
    name = var_name.replace('VR_', '')
    words = name.split('_')
    sigla = ''
    for word in words:
        if word.upper() in [
            'AO', 'AE', 'VD', 'VE', 'SC', 'A4C', 'A2C', 'FAC', 'COMP', 'MVE', 'ERP', 
            'PPVE', 'SEPTO', 'PSAP', 'VCI', 'INDICE', 'REL', 'LINHA', 'FETEICHHOLZ', 
            'FESIMPSON', 'SUPCORP', 'PESOPACIENTE', 'ALTURAPACIENTE', 'IMC', 
            'DESCRICAOIMC', 'SGL', 'DPDTVE', 'SLINHA', 'MAPS', 'VAD', 'BT', 'EVD', 
            'VATL', 'GLSVD', 'FWSVD', 'DSATL', 'DPDT', 'VEL', 'REG', 'PPICO', 'AD', 
            'DT', 'SV', 'JUNCAO', 'ASC', 'PROX', 'ARCOAO', 'VSVE', 'VEDI', 'VDF', 
            'VSF', 'PEC', 'PAREDES', 'REPOUSO', 'STRESS'
        ]:
            sigla += word.upper()
        else:
            sigla += word[0].upper() if word else ''
    return sigla[:10]

# Função para gerar comando SQL
def generate_sql_insert(var_name, description, sigla):
    cod_unidade_medida = 1
    cod_usuario = 4
    dthr_ult_modificacao = 'CURRENT_TIMESTAMP'
    casas_decimais = 2 if any(x in var_name.upper() for x in ['INDEX', 'REL', 'SC']) else None
    sql = f"""INSERT INTO VARIAVEIS (
        NOME, VARIAVEL, DESCRICAO, CODUNIDADEMEDIDA, SIGLA, 
        ABREVIACAO, CASASDECIMAIS, CODUSUARIO, DTHRULTMODIFICACAO
    ) VALUES (
        '{description}', '{var_name}', '{description}', 
        {cod_unidade_medida}, '{sigla}', '{sigla}', 
        {casas_decimais if casas_decimais is not None else 'NULL'}, 
        {cod_usuario}, {dthr_ult_modificacao}
    );"""
    return sql

# Função principal
def main():
    # Configurações do banco Firebird
    db_host = 'localhost'  # Ajuste conforme necessário
    db_path = 'C:/path/to/your/database.fdb'  # Caminho do banco
    db_user = 'SYSDBA'  # Usuário do banco
    db_password = 'masterkey'  # Senha do banco

    # Obtém siglas e variáveis existentes do banco
    existing_siglas, existing_variaveis = get_existing_variables(db_host, db_path, db_user, db_password)

    # Extrai variáveis do arquivo .cs
    cs_file = 'EcoModelo02.Designer.cs'
    cs_variables = extract_variables_from_cs(cs_file)

    # Gera comandos SQL apenas para variáveis novas
    sql_commands = []
    for var in sorted(cs_variables):
        sigla = generate_sigla(var)
        # Pula se SIGLA ou VARIAVEL já existem
        if sigla in existing_siglas or var in existing_variaveis:
            print(f"Pulando {var} (SIGLA: {sigla}) - já existe no banco.")
            continue
        description = generate_description(var)
        sql = generate_sql_insert(var, description, sigla)
        sql_commands.append(sql)
        # Adiciona a nova sigla e variável aos conjuntos para evitar conflitos no loop
        existing_siglas.add(sigla)
        existing_variaveis.add(var)

    # Salva os comandos em um arquivo
    with open('insert_variaveis.sql', 'w', encoding='utf-8') as f:
        for sql in sql_commands:
            f.write(sql + '\n')

    print(f"Gerados {len(sql_commands)} comandos SQL. Arquivo salvo como 'insert_variaveis.sql'.")

if __name__ == '__main__':
    main()