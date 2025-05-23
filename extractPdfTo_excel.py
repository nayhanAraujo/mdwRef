import os
os.environ["PATH"] += os.pathsep + r"C:\Program Files\gs\gs10.05.1\bin"
import camelot

# Tente com flavor stream primeiro
tabelas = camelot.read_pdf(
    r"C:\Users\nayhan\Documents\PROJETOS AZURE\6- AZURE - REFERENCIAS\DIcom16.pdf",
    pages='1352-1359',  # Intervalo de páginas mais limpo
    flavor='stream',    # Tente stream primeiro
    strip_text='\u200b\n'  # Limpeza automática
)

# Verifique quantas tabelas foram encontradas
print(f"Foram encontradas {len(tabelas)} tabelas")

# Exporte todas as tabelas encontradas
for i, tabela in enumerate(tabelas):
    df = tabela.df
    df.to_excel(f"tabela_extraida_{i+1}.xlsx", engine="openpyxl", index=False)