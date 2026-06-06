import argparse
import datetime
import os
import sys
import json
from dotenv import load_dotenv
from imap_tools import MailBox, A

# Cargar variables de entorno
load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_SERVER = os.getenv("EMAIL_SERVER")
EMAIL_FOLDER = os.getenv("EMAIL_FOLDER")

# Validar credenciales, servidor y carpeta indicando exactamente cuál falta
faltantes = []
if not EMAIL_USER:
    faltantes.append("EMAIL_USER")
if not EMAIL_PASS:
    faltantes.append("EMAIL_PASS")
if not EMAIL_SERVER:
    faltantes.append("EMAIL_SERVER")
if not EMAIL_FOLDER:
    faltantes.append("EMAIL_FOLDER")

if faltantes:
    print(f"❌ Error: Faltan definir o están vacías las siguientes variables en tu archivo .env: {', '.join(faltantes)}")
    sys.exit(1)

# Configurar argumentos de línea de comandos para las fechas
parser = argparse.ArgumentParser(
    description="Descarga facturas PDF desde el servidor de correo Cromosol.",
    usage="python descarga_mail.py -d YYYY-MM-DD [-t YYYY-MM-DD]"
)
parser.add_argument("--desde", "-d", required=True, help="Fecha inicial en formato YYYY-MM-DD (Requerido)")
parser.add_argument("--hasta", "-t", required=False, help="Fecha final en formato YYYY-MM-DD (Opcional, por defecto: hoy)")
args = parser.parse_args()

try:
    fecha_desde = datetime.datetime.strptime(args.desde.strip(), "%Y-%m-%d").date()

    if args.hasta:
        fecha_hasta = datetime.datetime.strptime(args.hasta.strip(), "%Y-%m-%d").date()
    else:
        # Por defecto, hasta hoy
        fecha_hasta = datetime.date.today()
        print(f"ℹ️ Fecha final (--hasta) no especificada. Usando por defecto: {fecha_hasta}")
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
DIR_LOGS = os.path.join(CARPETA_BASE, "logs")

# Asegurar que las carpetas existan
for carpeta in [DIR_PENDIENTES, DIR_PROCESADOS, DIR_ERRORES, DIR_LOGS]:
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)
        print(f"📁 Carpeta creada: {carpeta}")

# Ruta del archivo de caché de correos descargados
ARCHIVO_CACHE = os.path.join(DIR_LOGS, "descargados_mails.json")

def cargar_cache():
    if os.path.exists(ARCHIVO_CACHE):
        try:
            with open(ARCHIVO_CACHE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Advertencia: No se pudo leer la caché {ARCHIVO_CACHE}: {e}")
    return {}

def guardar_cache(cache):
    try:
        with open(ARCHIVO_CACHE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error al guardar la caché: {e}")

def comprobar_correo_procesado(msg_id, cache, dir_pendientes, dir_procesados, dir_errores):
    if not msg_id or msg_id not in cache:
        return False
    filenames = cache[msg_id]
    if not filenames:
        # Si el correo no tiene adjuntos PDF relevantes (la lista está vacía), lo consideramos procesado
        return True
    
    # Verificar que todos los adjuntos que se descargaron sigan existiendo en disco
    for name in filenames:
        ruta_pen = os.path.join(dir_pendientes, name)
        ruta_pro = os.path.join(dir_procesados, name)
        ruta_err = os.path.join(dir_errores, name)
        if not (os.path.exists(ruta_pen) or os.path.exists(ruta_pro) or os.path.exists(ruta_err)):
            return False  # Si falta al menos uno, forzamos re-descarga
    return True

# Cargar caché actual
cache_descargados = cargar_cache()

# Para date_lt necesitamos el día siguiente a la fecha_hasta para que sea inclusivo
fecha_hasta_exclusivo = fecha_hasta + datetime.timedelta(days=1)

print(f"🔌 Conectando a {EMAIL_SERVER}...")
try:
    with MailBox(EMAIL_SERVER, timeout=15).login(EMAIL_USER, EMAIL_PASS) as mailbox:
        mailbox.folder.set(EMAIL_FOLDER)
        
        print(f"🔍 Buscando cabeceras desde {fecha_desde} hasta {fecha_hasta} (inclusive)...")
        # Consultar mensajes en el rango de fechas (solicitando solo cabeceras primero)
        query = A(date_gte=fecha_desde, date_lt=fecha_hasta_exclusivo)
        
        correos_a_descargar = []
        mapa_uid_msgid = {}
        contador_evaluados = 0
        
        for msg in mailbox.fetch(query, headers_only=True):
            contador_evaluados += 1
            
            # Obtener el identificador único del correo
            msg_id_tuple = msg.headers.get('message-id')
            msg_id = msg_id_tuple[0] if msg_id_tuple else None
            if not msg_id:
                msg_id = f"UID_{msg.uid}"
            
            msg_id = msg_id.strip()
            
            # Comprobar si ya existe localmente y en la caché
            if comprobar_correo_procesado(msg_id, cache_descargados, DIR_PENDIENTES, DIR_PROCESADOS, DIR_ERRORES):
                # Mensaje de depuración más corto para evitar inundar la consola
                print(f"   ⏭️ Saltado (ya descargado): Subject: '{msg.subject}' (Msg-ID: {msg_id})")
                continue
                
            correos_a_descargar.append(msg.uid)
            mapa_uid_msgid[msg.uid] = msg_id
            print(f"   📌 Agendado para descargar: Subject: '{msg.subject}' ({msg.date.strftime('%Y-%m-%d')})")
            
        print(f"\n📊 Resumen de evaluación: {contador_evaluados} correos analizados.")
        print(f"📥 Correos nuevos o que requieren re-descarga: {len(correos_a_descargar)}")
        
        contador_descargas = 0
        
        # Descargar los correos agendados en un solo lote
        if correos_a_descargar:
            criterio_uids = A(uid=correos_a_descargar)
            print("📦 Iniciando descarga en lote...")
            
            for msg in mailbox.fetch(criterio_uids):
                uid = msg.uid
                msg_id_tuple = msg.headers.get('message-id')
                fallback_msg_id = msg_id_tuple[0] if msg_id_tuple else f"UID_{uid}"
                msg_id = mapa_uid_msgid.get(uid, fallback_msg_id).strip()
                print(f"   📧 Descargando adjuntos de: '{msg.subject}'")
                
                filenames = []
                try:
                    for att in msg.attachments:
                        # Filtrar solo archivos PDF
                        if att.filename.lower().endswith('.pdf'):
                            # Verificar si por las dudas ya existe el archivo en alguna carpeta
                            ruta_pendiente = os.path.join(DIR_PENDIENTES, att.filename)
                            ruta_procesado = os.path.join(DIR_PROCESADOS, att.filename)
                            ruta_error = os.path.join(DIR_ERRORES, att.filename)
                            
                            if os.path.exists(ruta_pendiente) or os.path.exists(ruta_procesado) or os.path.exists(ruta_error):
                                print(f"      ⏭️ Saltado adjunto (archivo físico ya existe): {att.filename}")
                                filenames.append(att.filename)
                                continue
                                
                            with open(ruta_pendiente, 'wb') as f:
                                f.write(att.payload)
                            print(f"      ✅ Descargado adjunto: {att.filename} ({att.content_type})")
                            filenames.append(att.filename)
                            contador_descargas += 1
                    
                    # Actualizar e incrementalmente guardar la caché
                    cache_descargados[msg_id] = filenames
                    guardar_cache(cache_descargados)
                    
                except Exception as file_err:
                    print(f"      ❌ Error al guardar adjuntos de correo UID {uid}: {file_err}")
                    
        print(f"✨ Proceso de descarga finalizado. Total descargados: {contador_descargas}")

except Exception as e:
    print(f"🔥 Error en la conexión/descarga de correo: {e}")
    sys.exit(1)
