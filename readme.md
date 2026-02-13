🤖 Automatización de Procesamiento de Facturas (Cromosol)
Este proyecto es un sistema de procesamiento por lotes (batch processing) diseñado para extraer datos de facturas en PDF (específicamente del proveedor Cromosol), validarlos matemáticamente y generar un archivo JSON compatible con la inyección de datos en Cianbox (vía Tampermonkey).

📋 Características Principales
Extracción Inteligente: Utiliza pdfplumber con estrategias de corte por coordenadas y escaneo vertical para leer tablas sin líneas visibles.

Validación Contable: Realiza doble chequeo matemático:

Horizontal: Cantidad x Precio Unitario = Subtotal de Línea.

Vertical: Neto + IVA + Percepciones = Total del Comprobante.

Tolerancia a Redondeos: Admite una diferencia máxima de $0.09 para absorber errores de coma flotante.

Clasificación Automática: Mueve los archivos a carpetas de "Éxito" o "Error" según el resultado.

Auditoría: Genera un log CSV detallado con el motivo de cada fallo.

🏗️ Arquitectura del Sistema
El sistema sigue un patrón de Tubería de Procesamiento (Pipeline) basado en el estado de los archivos.

Estructura de Carpetas
El script genera y gestiona automáticamente la siguiente estructura:

Plaintext
/automatizacion-facturas
│
├── 📁 01_pendientes       <-- [INPUT] Aquí se depositan los PDFs nuevos (manualmente o vía mail).
│
├── 📁 02_procesados       <-- [OK] PDFs validados correctamente se mueven aquí.
│
├── 📁 03_errores          <-- [FAIL] PDFs con errores de lectura o validación matemática.
│
├── 📁 logs
│    └── 📄 audit_log.csv  <-- Bitácora histórica (Fecha, Archivo, Motivo del Error).
│
├── 📄 procesador_batch.py <-- Script Principal (Orquestador).
│
└── 📄 lote_cianbox.json   <-- [OUTPUT] El resultado final listo para Tampermonkey.
Flujo de Datos
Ingesta: El script busca todos los archivos .pdf en 01_pendientes.

Parser (Cromosol):

Detecta tipo de comprobante (Factura/Nota de Crédito/Débito) y Letra.

Aísla la tabla de productos mediante coordenadas fijas (Corte en X=88 para separar Código de Descripción).

Escanea el pie de página buscando verticalmente las columnas "TOTAL", "NETO", "I.V.A." e "IIBB".

Validación: Compara los valores leídos con los calculados.

Enrutamiento:

Si es válido: Mueve el PDF a 02_procesados y agrega los datos a lote_cianbox.json.

Si es inválido: Mueve el PDF a 03_errores y escribe el detalle en audit_log.csv.

🚀 Instrucciones de Uso
1. Requisitos Previos
Necesitas tener Python 3 instalado. Luego, instala la librería de manipulación de PDFs:

Bash
pip install pdfplumber
2. Ejecución
Coloca tus facturas PDF en la carpeta 01_pendientes.

Nota: Si la carpeta no existe, ejecuta el script una vez y la creará sola.

Abre una terminal en la carpeta del proyecto y ejecuta:

Bash
python procesador_batch.py
Observa la salida en la consola. Verás el progreso archivo por archivo:

✅ APROBADO

❌ RECHAZADO: Error Suma Fiscal...

3. Resultado
Abre el archivo lote_cianbox.json. Copia su contenido.

Pégalo en tu script de Tampermonkey en Cianbox para realizar la importación masiva.

⚙️ Configuración y Ajustes
Puedes modificar las constantes al inicio del archivo procesador_batch.py:

TOLERANCIA = 0.09: Ajusta este valor si las facturas tienen problemas de redondeo mayores.

Coordenadas de Corte: Si el proveedor cambia el diseño de la factura, deberás ajustar la lista cortes dentro de la función procesar_archivo_individual.

🛠️ Solución de Problemas (Troubleshooting)
El archivo terminó en 03_errores. ¿Por qué?

Revisa el archivo logs/audit_log.csv. Allí encontrarás la razón exacta:

Error Suma Productos: La multiplicación de cantidades por precios no coincide con el neto. Posible error de lectura en la columna "Cantidad".

Error Suma Fiscal: La suma de impuestos no da el total. Posible percepción de IIBB no detectada o error de lectura en el Total.

Excepción Python: El PDF tiene un formato corrupto o inesperado.

Desarrollado para automatización de ingreso de stock en Cianbox.