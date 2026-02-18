import datetime
import os
from dotenv import load_dotenv
from imap_tools import MailBox, A, AND

# Cargar variables de entorno
load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_SERVER = os.getenv("EMAIL_SERVER", "mail.equipstore.com.ar")

# Configurar carpeta de descarga relativa al proyecto (para que funcione en Mac/Windows)
CARPETA_BASE = os.getcwd()
DIR_PENDIENTES = os.path.join(CARPETA_BASE, "01_pendientes")

# Asegurar que la carpeta exista
if not os.path.exists(DIR_PENDIENTES):
    os.makedirs(DIR_PENDIENTES)

# get all attachments for each email from INBOX folder
with MailBox(EMAIL_SERVER).login(EMAIL_USER, EMAIL_PASS) as mailbox:
#    for folder in mailbox.folder.list('INBOX'):
#        print(folder['flags'], folder['delim'], folder['name'])

# '_year', '_month', '_day' FECHA DESDE
    fecha=datetime.date(2026, 1, 1) # Ajustado a una fecha más lógica (pasado)

    mailbox.folder.set('INBOX.Facturas.Facturas cromosol')
#    for msg in mailbox.fetch(A(from_="comprobantes@comprobantes.cromosol.com"), charset='utf8', subject='Envío FC 0021-00400608 del 19-04-2022 Cromosol'):
    for msg in mailbox.fetch(A(date_gte=fecha)):
        for att in msg.attachments:
            print(att.filename, att.content_type)
            ruta_destino = os.path.join(DIR_PENDIENTES, att.filename)
            with open(ruta_destino, 'wb') as f:
                f.write(att.payload)
            print(f"Descargado en: {ruta_destino}")

print("✅ Proceso de descarga desde mail finalizado.")
