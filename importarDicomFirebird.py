import pandas as pd
import firebird.driver as fbd
from firebird.driver import connect, Error as FBError
from deep_translator import GoogleTranslator
import time

# Configurar o tradutor

def traduzir_google(descricao_en):
    try:
        if not descricao_en or pd.isna(descricao_en):
            return None
        
        time.sleep(2)  # Delay para evitar bloqueios
        traducao = GoogleTranslator(source='en', target='pt').translate(descricao_en)
        return traducao[:255] if traducao else descricao_en[:255]
        
    except Exception as e:
        print(f"Erro na tradução de '{descricao_en}': {e}")
        return descricao_en[:255]

try:
    # 1. Carregar a planilha Excel
    caminho_excel = "tabela_extraida_10.xlsx"
    df = pd.read_excel(caminho_excel)
    df = df[df['Code Value'].notna() & (df['Code Value'] != '')]

    # 2. Conectar ao Firebird
    try:
        con = connect(
            r"nayhan/3052:C:\Users\nayhan\Documents\PROJETOS AZURE\6- AZURE - REFERENCIAS\REFERENCIAS\BD\REFERENCIAS.FDB",
            user="SYSDBA",
            password="masterkey"
        )
        print("Conexão com o Firebird estabelecida com sucesso!")
        
        cur = con.cursor()
        batch_size = 50  # Reduzi o batch_size para commits mais frequentes
        total_inseridos = 0
        
        # 3. Processar cada linha
        for index, row in df.iterrows():
            try:
                # Preparar valores
                tipocodigo = 'DICOM'
                codigo = str(row['Code Value']).strip()[:50]  # CODIGO VARCHAR(50)
                descricao_en = str(row['Code Meaning']).strip() if pd.notna(row['Code Meaning']) else None
                unidade = str(row['Units']).strip() if pd.notna(row['Units']) else None
                
                # Traduzir descrição para português
                if descricao_en:
                    descricao_pt = traduzir_google(descricao_en)
                    print(f"Traduzindo: {descricao_en} -> {descricao_pt}")
                else:
                    descricao_pt = None
                
                # SQL atualizado com todas as colunas
                sql = """INSERT INTO CODIGO_UNIVERSAL 
                         (TIPO_CODIGO, CODIGO, DESCRICAO, DESCRICAOPTBR, UNIDADE) 
                         VALUES (?, ?, ?, ?, ?)"""
                
                # Executar a inserção
                cur.execute(sql, (tipocodigo, codigo, descricao_en, descricao_pt, unidade))
                total_inseridos += 1
                
                # Commit periódico
                if (index + 1) % batch_size == 0:
                    con.commit()
                    print(f"Commit realizado após {index + 1} registros")
                    
            except FBError as e:
                print(f"\nERRO ao inserir linha {index + 1}: {e}")
                print(f"Dados: CODIGO={codigo}, DESCRICAO_EN={descricao_en}, DESCRICAO_PT={descricao_pt}")
                con.rollback()
            except Exception as e:
                print(f"\nERRO inesperado na linha {index + 1}: {e}")
                con.rollback()
        
        # Commit final
        con.commit()
        print(f"\nProcesso concluído! Total de {total_inseridos} registros inseridos com sucesso.")
        
        # Verificar se os dados foram inseridos corretamente
        cur.execute("SELECT CODIGO, DESCRICAO, DESCRICAOPTBR FROM CODIGO_UNIVERSAL WHERE TIPO_CODIGO = 'DICOM' ORDER BY CODIGO DESC ROWS 5")
        exemplos = cur.fetchall()
        
        print("\nÚltimos 5 registros inseridos como exemplo:")
        for reg in exemplos:
            print(f"Código: {reg[0]}\nInglês: {reg[1]}\nPortuguês: {reg[2]}\n{'-'*50}")
        
    except FBError as e:
        print(f"Erro na conexão com o Firebird: {e}")
    except Exception as e:
        print(f"Erro inesperado na conexão: {e}")
    finally:
        if 'con' in locals() and con is not None:
            con.close()
            print("Conexão com o Firebird fechada.")

except Exception as e:
    print(f"Erro geral no processamento: {e}")



    # Configurar o tradutor
