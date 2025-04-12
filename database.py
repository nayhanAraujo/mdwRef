import firebird.driver as fbd

def conectar():
    return fbd.connect(
        r"nayhan/3052:C:\Users\nayhan\Documents\PROJETOS AZURE\6- AZURE - REFERENCIAS\REFERENCIAS\BANCO REFERENCIA\BD\REFERENCIAS.FDB",
        user="SYSDBA",
        password="masterkey"
    )
