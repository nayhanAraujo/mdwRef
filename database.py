import firebird.driver as fbd

def conectar():
    return fbd.connect(
        r"localhost/3052:C:\CAMINHO\DO\SEU\BANCO\REFERENCIAS.FDB",
        user="SYSDBA",
        password="masterkey"
    )
