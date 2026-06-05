# 📧 Descargador de Facturas desde Correo (`descarga_mail.py`)

Este script automatiza la descarga de archivos de facturas en formato PDF adjuntos en correos electrónicos. Se conecta a una casilla de correo usando el protocolo IMAP, filtra los mensajes por rango de fecha y descarga únicamente los archivos PDF nuevos.

---

## 🛠️ Requisitos e Instalación

Para utilizar esta herramienta, debes instalar las dependencias necesarias de Python (`imap-tools` y `python-dotenv`).

Desde la terminal en el directorio del proyecto, ejecuta:
```bash
venv/bin/pip install imap-tools python-dotenv
```

---

## ⚙️ Configuración (.env)

Antes de ejecutar la descarga, debes configurar las credenciales y datos de tu servidor en el archivo `.env` en la raíz del proyecto. Si no tienes este archivo, puedes crear una copia de `.env.example` y renombrarlo a `.env`.

Las variables obligatorias son:
```ini
# Servidor de correo entrante (IMAP)
EMAIL_SERVER=mail.equipstore.com.ar

# Dirección de correo electrónico y contraseña
EMAIL_USER=tu_usuario@equipstore.com.ar
EMAIL_PASS=tu_contraseña

# Carpeta IMAP donde se encuentran los correos de las facturas
EMAIL_FOLDER="INBOX.Facturas.Facturas cromosol"
```

---

## 🚀 Modo de Uso y Parámetros

El script permite filtrar los correos descargados por un rango de fechas. Las fechas se pasan como argumentos de línea de comandos en formato `YYYY-MM-DD`.

### 1. Ejecución por defecto (Sin parámetros)
Si ejecutas el script sin especificar parámetros, descargará los correos de los **últimos 7 días** hasta el día de **hoy** (inclusive). Además, te mostrará un recordatorio de cómo usar los parámetros:
```bash
venv/bin/python descarga_mail.py
```

### 2. Ejecución con rango de fechas completo
Para buscar correos entre dos fechas específicas (por ejemplo, del 1 al 15 de mayo de 2026):
```bash
venv/bin/python descarga_mail.py --desde 2026-05-01 --hasta 2026-05-15
```

O usando los atajos cortos:
```bash
venv/bin/python descarga_mail.py -d 2026-05-01 -t 2026-05-15
```

### 3. Ejecución especificando solo fecha inicial o final
* Descargar correos desde el 20 de mayo de 2026 hasta hoy:
  ```bash
  venv/bin/python descarga_mail.py --desde 2026-05-20
  ```
* Descargar correos de los últimos 7 días hasta el 10 de mayo de 2026:
  ```bash
  venv/bin/python descarga_mail.py --hasta 2026-05-10
  ```

---

## 🧠 Optimización y Control de Duplicados

* **Filtro de archivos**: Solo descarga archivos con extensión `.pdf`.
* **Prevención de duplicaciones**: Para evitar volver a descargar e ingresar facturas que ya han sido procesadas, el script busca el nombre del archivo PDF en tres directorios locales antes de descargarlo:
  1. `01_pendientes/` (comprobantes descargados sin procesar)
  2. `02_procesados/` (comprobantes validados con éxito)
  3. `03_errores/` (comprobantes con errores matemáticos o de formato)
  
  Si el archivo ya existe en cualquiera de estas carpetas, el script omitirá su descarga imprimiendo: `⏭️ Saltado (ya existe localmente): nombre_archivo.pdf`.
* **Logs en tiempo real**: Durante la ejecución, verás en la terminal el asunto, el remitente y la fecha del correo que se está escaneando para que puedas monitorear el progreso del script.
