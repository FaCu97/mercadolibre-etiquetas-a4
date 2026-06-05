import argparse
import datetime
import os
import sys
from dotenv import load_dotenv
from imap_tools import MailBox, A

# Cargar variables de entorno
load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_SERVER = os.getenv("EMAIL_SERVER")
EMAIL_FOLDER = os.getenv("EMAIL_FOLDER")

# Validar credenciales, servidor y carpeta
if not EMAIL_USER or not EMAIL_PASS or not EMAIL_SERVER or not EMAIL_FOLDER:
    print("❌ Error: Debes configurar EMAIL_USER, EMAIL_PASS, EMAIL_SERVER y EMAIL_FOLDER en el archivo .env")
    sys.exit(1)

# Configurar argumentos de línea de comandos para las fechas
parser = argparse.ArgumentParser(
    description="Descarga facturas PDF desde el servidor de correo Cromosol.",
    usage="python descarga_mail.py [-d YYYY-MM-DD] [-t YYYY-MM-DD]"
)
parser.add_argument("--desde", "-d", help="Fecha inicial en formato YYYY-MM-DD (por defecto: hace 7 días)")
parser.add_argument("--hasta", "-t", help="Fecha final en formato YYYY-MM-DD (por defecto: hoy)")
args = parser.parse_args()

# Si se ejecuta sin argumentos, mostrar cómo se usa el script para parametrizar fechas
if len(sys.argv) == 1:
    print("ℹ️  Modo de uso:")
    print("   python descarga_mail.py --desde YYYY-MM-DD --hasta YYYY-MM-DD")
    print("   python descarga_mail.py -d YYYY-MM-DD -t YYYY-MM-DD")
    print("💡 Ejecutando ahora con el rango por defecto (últimos 7 días hasta hoy)...")
    print("-" * 60)

try:
    if args.desde:
        fecha_desde = datetime.datetime.strptime(args.desde.strip(), "%Y-%m-%d").date()
    else:
        # Por defecto, desde hace 7 días
        fecha_desde = (datetime.date.today() - datetime.timedelta(days=7))
        print(f"ℹ️ Fecha inicial (--desde) no especificada. Usando defecto: {fecha_desde}")

    if args.hasta:
        fecha_hasta = datetime.datetime.strptime(args.hasta.strip(), "%Y-%m-%d").date()
    else:
        # Por defecto, hasta hoy
        fecha_hasta = datetime.date.today()
        print(f"ℹ️ Fecha final (--hasta) no especificada. Usando defecto: {fecha_hasta}")
except ValueError as e:
    print(f"\n❌ Error al parsear fechas de los argumentos (formato esperado: YYYY-MM-DD): {e}")
    print("\nModo de uso correcto:")
    parser.print_help()
    sys.exit(1)

# Configurar carpetas del proyecto para verificar duplicados
CARPETA_BASE = os.getcwd()
DIR_PENDIENTES = os.path.join(CARPETA_BASE, "01_pendientes")
DIR_PROCESADOS = os.path.join(CARPETA_BASE, "02_procesados")
DIR_ERRORES = os.path.join(CARPETA_BASE, "03_errores")

# Asegurar que las carpetas existan
for carpeta in [DIR_PENDIENTES, DIR_PROCESADOS, DIR_ERRORES]:
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)
        print(f"📁 Carpeta creada: {carpeta}")

# Para date_lt necesitamos el día siguiente a la fecha_hasta para que sea inclusivo
fecha_hasta_exclusivo = fecha_hasta + datetime.timedelta(days=1)

print(f"🔍 Buscando correos desde {fecha_desde} hasta {fecha_hasta} (inclusive)...")

# Obtener adjuntos
try:
    with MailBox(EMAIL_SERVER).login(EMAIL_USER, EMAIL_PASS) as mailbox:
        mailbox.folder.set(EMAIL_FOLDER)
        
        # Consultar mensajes en el rango de fechas
        # imap_tools usa date_gte (>=) y date_lt (<)
        query = A(date_gte=fecha_desde, date_lt=fecha_hasta_exclusivo)
        
        contador_descargas = 0
        for msg in mailbox.fetch(query):
            print(f"📧 Evaluando correo: '{msg.subject}' de {msg.from_} ({msg.date.strftime('%Y-%m-%d')})")
            
            for att in msg.attachments:
                # Filtrar solo archivos PDF
                if att.filename.lower().endswith('.pdf'):
                    # Verificar si ya existe en alguna de las carpetas del proyecto
                    ruta_pendiente = os.path.join(DIR_PENDIENTES, att.filename)
                    ruta_procesado = os.path.join(DIR_PROCESADOS, att.filename)
                    ruta_error = os.path.join(DIR_ERRORES, att.filename)
                    
                    if os.path.exists(ruta_pendiente) or os.path.exists(ruta_procesado) or os.path.exists(ruta_error):
                        print(f"   ⏭️ Saltado (ya existe localmente): {att.filename}")
                        continue
                        
                    with open(ruta_pendiente, 'wb') as f:
                        f.write(att.payload)
                    print(f"   ✅ Descargado: {att.filename} ({att.content_type})")
                    contador_descargas += 1
                    
        print(f"✨ Proceso de descarga finalizado. Total descargados: {contador_descargas}")

except Exception as e:
    print(f"🔥 Error en la conexión/descarga de correo: {e}")
    sys.exit(1)
