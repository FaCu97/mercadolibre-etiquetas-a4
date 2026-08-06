import pdfplumber
import re
import json
import os
import shutil
import csv
from datetime import datetime
import glob
import concurrent.futures
import threading
from google import genai
from dotenv import load_dotenv
from google.genai import types

# ==============================================================================
# 1. CONFIGURACIÓN GENERAL
# ==============================================================================
CARPETA_BASE = os.getcwd()
DIR_ENTRADA = os.path.join(CARPETA_BASE, "01_pendientes")
DIR_SALIDA_OK = os.path.join(CARPETA_BASE, "02_procesados")
DIR_SALIDA_ERROR = os.path.join(CARPETA_BASE, "03_errores")
DIR_LOGS = os.path.join(CARPETA_BASE, "logs")
ARCHIVO_JSON_FINAL = os.path.join(CARPETA_BASE, "lote_cianbox.json")
ARCHIVO_LOG_CSV = os.path.join(DIR_LOGS, "audit_log.csv")
ARCHIVO_PROCESADAS_CSV = os.path.join(DIR_LOGS, "procesadas.csv")
ARCHIVO_ERRORES_CSV = os.path.join(DIR_LOGS, "errores.csv")

# Tolerancia para diferencias de redondeo (en pesos)
TOLERANCIA = 0.09 

# --- LISTAS DE REFERENCIA PARA LA IA ---
# Agrega aquí los nombres EXACTOS de tus proveedores tal como están en tu sistema/Cianbox
PROVEEDORES_CONOCIDOS = [
    "CROMOSOL",
    "ABC ACCESORIOS",
    "KOMPUSUR SA",
]

PROVINCIAS_VALIDAS = [
    "Capital Federal", "Ciudad de Buenos Aires", "Santa Fe", 
    "Córdoba", "Tucuman", "Misiones", "Corrientes", "Mendoza", 
    "Buenos Aires", "Provincia de Buenos Aires"
]

# Cargar variables de entorno (.env) para la API Key
load_dotenv()

# Bloqueo para evitar que los prints y logs se mezclen entre hilos
print_lock = threading.RLock()

# Variable global para almacenar el historial de facturas procesadas
HISTORIAL_PROCESADO = set()

# ==============================================================================
# 2. HERRAMIENTAS DE LOGGING Y ARCHIVOS
# ==============================================================================
def inicializar_carpetas():
    for d in [DIR_ENTRADA, DIR_SALIDA_OK, DIR_SALIDA_ERROR, DIR_LOGS]:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"📁 Carpeta creada: {d}")

    # Crear CSVs si no existen
    for archivo in [ARCHIVO_LOG_CSV, ARCHIVO_PROCESADAS_CSV, ARCHIVO_ERRORES_CSV]:
        if not os.path.exists(archivo):
            with open(archivo, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Fecha", "Archivo", "Proveedor", "Tipo", "Numero", "Estado", "Motivo", "Diferencia"])

def registrar_log(archivo, proveedor, tipo, numero, estado, motivo, diferencia="0.00"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp, archivo, proveedor, tipo, numero, estado, motivo, diferencia]
    
    with print_lock:
        print(f"   📝 Log: {estado} - {motivo}")
        
        # Enrutamiento de logs
        if estado in ["OK", "CARGA_EXITOSA"]:
            target = ARCHIVO_PROCESADAS_CSV
        elif "ERROR" in estado or "RECHAZADO" in estado:
            target = ARCHIVO_ERRORES_CSV
        else:
            target = ARCHIVO_LOG_CSV # Informativo (YA_PROCESADA, etc)

        with open(target, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row)

def mover_archivo(ruta_origen, carpeta_destino):
    nombre_archivo = os.path.basename(ruta_origen)
    destino = os.path.join(carpeta_destino, nombre_archivo)
    
    # Si ya existe, le agregamos un timestamp para no sobrescribir
    if os.path.exists(destino):
        base, ext = os.path.splitext(nombre_archivo)
        timestamp = datetime.now().strftime("%H%M%S")
        destino = os.path.join(carpeta_destino, f"{base}_{timestamp}{ext}")
        
    shutil.move(ruta_origen, destino)

def cargar_historial_procesado():
    """
    Lee procesadas.csv y carga en memoria las facturas que ya fueron
    procesadas correctamente (OK) o cargadas en Cianbox (CARGA_EXITOSA).
    """
    global HISTORIAL_PROCESADO
    HISTORIAL_PROCESADO.clear()
    
    if not os.path.exists(ARCHIVO_PROCESADAS_CSV):
        return

    try:
        with open(ARCHIVO_PROCESADAS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None) # Saltar encabezado
            for row in reader:
                if len(row) < 6: continue
                # Estructura: Fecha, Archivo, Proveedor, Tipo, Numero, Estado, ...
                prov, tipo, nro, estado = row[2], row[3], row[4], row[5]
                
                if estado in ["OK", "CARGA_EXITOSA"]:
                    # Clave única normalizada: PROVEEDOR_TIPO_NUMERO
                    key = f"{prov.strip().upper()}_{tipo.strip().upper()}_{nro.strip()}"
                    HISTORIAL_PROCESADO.add(key)
        
        print(f"📚 Historial cargado: {len(HISTORIAL_PROCESADO)} comprobantes ya procesados.")
    except Exception as e:
        print(f"⚠️ Error leyendo historial: {e}")

# ==============================================================================
# 3. EL PARSER (LÓGICA DE EXTRACCIÓN - BASE V12)
# ==============================================================================
def str_to_float(precio_str):
    if not precio_str: return 0.0
    clean = re.sub(r'[^\d,]', '', precio_str).replace('.', '')
    try: return float(clean.replace(',', '.'))
    except ValueError: return 0.0

def float_to_str(valor_float):
    # Asegura que el valor tenga 2 decimales y luego formatea a estilo argentino
    return "{:,.2f}".format(round(valor_float, 2)).replace(",", "X").replace(".", ",").replace("X", ".")

def limpiar_texto_palabra(texto):
    """Limpia el texto de una palabra para comparación (quita espacios extra, etc.)."""
    return texto.strip().upper()

def obtener_valor_debajo_de_header(words, header, margen_vertical=60):
    x_centro_header = (header['x0'] + header['x1']) / 2
    
    # Encontramos si hay algún otro encabezado principal a la derecha de este en la misma línea
    COLUMNAS_PRINCIPALES = ["SUBTOTAL", "DESCUENTO", "NETO", "I.V.A.", "PERC.", "TOTAL"]
    otro_headers_derecha = []
    for w in words:
        if abs(w['top'] - header['top']) < 4 and w['x0'] > header['x1']:
            if w['text'].strip().upper() in COLUMNAS_PRINCIPALES:
                otro_headers_derecha.append(w)
                
    if otro_headers_derecha:
        otro_headers_derecha.sort(key=lambda w: w['x0'])
        x_derecha_limite = otro_headers_derecha[0]['x0']
    else:
        x_derecha_limite = header['x1'] + 120
        
    y_min = header['bottom']
    y_max = header['bottom'] + margen_vertical
    
    valores_encontrados = []
    for w in words:
        if re.search(r'\d+,\d{2}', w['text']):
            mid_x = (w['x0'] + w['x1']) / 2
            if x_centro_header - 50 < mid_x < x_derecha_limite:
                if y_min < w['top'] < y_max:
                    valores_encontrados.append(w)
                    
    if valores_encontrados:
        valores_encontrados.sort(key=lambda x: x['top'])
        valor_final = valores_encontrados[0]['text'].strip()
    else:
        valor_final = "0,00"
        
    palabras_derecha = [w['text'] for w in words if abs(w['top'] - header['top']) < 4 and w['x0'] > header['x1']]
    contexto = " ".join(palabras_derecha).split("TOTAL")[0].strip()
    
    return valor_final, contexto

def extraer_valor_por_columna(words, palabra_clave, margen_vertical=60):
    # Búsqueda de palabras múltiples (ej. "SUBTOTAL NETO")
    if " " in palabra_clave:
        parts = palabra_clave.split()
        cands_part0 = [w for w in words if w['text'].strip().upper() == parts[0]]
        for c0 in cands_part0:
            cands_part1 = [w for w in words if w['text'].strip().upper() == parts[1] and abs(w['top'] - c0['top']) < 4 and 0 < w['x0'] - c0['x1'] < 80]
            if cands_part1:
                c1 = cands_part1[0]
                header = {
                    'text': palabra_clave,
                    'x0': c0['x0'],
                    'x1': c1['x1'],
                    'top': c0['top'],
                    'bottom': c0['bottom']
                }
                return obtener_valor_debajo_de_header(words, header, margen_vertical)
                
    # Búsqueda normal
    candidatos = [w for w in words if w['text'].strip().upper() == palabra_clave]
    if not candidatos:
        candidatos = [w for w in words if palabra_clave in w['text'].upper()]
        if palabra_clave == "TOTAL":
            candidatos = [w for w in candidatos if "SUBTOTAL" not in w['text'].upper()]
            
    if not candidatos: return "0,00", ""
    
    # Si es "SUBTOTAL" y hay más de una, queremos el primero (Gross Subtotal)
    if palabra_clave == "SUBTOTAL" and len(candidatos) > 1:
        header = candidatos[0]
    else:
        header = candidatos[-1]
        
    return obtener_valor_debajo_de_header(words, header, margen_vertical)

# ==============================================================================
# 4. ESTRATEGIAS DE PARSEO (PROVEEDORES)
# ==============================================================================
def parsear_cromosol(page, full_text, ruta_pdf):
    # Retorna: (DatosJSON, ErrorMsg)
    # Si ErrorMsg es None, significa que salió OK.
    
    nombre_archivo = os.path.basename(ruta_pdf)
    # --- DEBUG TEMPORAL ---
    # print("--- INICIO DUMP PDF ---")
    # pie = page.crop((0, page.height * 0.60, page.width, page.height)) # Recorta el pie
    # words = pie.extract_words()
    # for w in words:
    #     # Imprime texto y coordenadas exactas
    #     if "TOTAL" in w['text'] or "NETO" in w['text'] or re.search(r'\d+,\d{2}', w['text']):
    #         print(f"Texto: '{w['text']}' | x0: {w['x0']:.2f} | top: {w['top']:.2f} | bottom: {w['bottom']:.2f}")
    # print("--- FIN DUMP PDF ---")
    try:
            # --- HEADER ---
            header_text = page.crop((0, 0, page.width, 250)).extract_text().upper()
            if "CREDITO" in header_text: tipo = "NOTA DE CREDITO"
            elif "DEBITO" in header_text: tipo = "NOTA DE DEBITO"
            else: tipo = "FACTURA"

            mueve_stock = True
            # --- REGLA DE NEGOCIO: NC CROMOSOL (STOCK) ---
            if tipo == "NOTA DE CREDITO":
                # Si es una bonificación por volumen, oferta, operación o arreglo, NO mueve stock
                if re.search(r'POR:\s*(VOLUMEN|OFERTA|OPERACI[OÓ]N|ARREGLO)|(VOLUMEN|OFERTA|OPERACI[OÓ]N|ARREGLO)\s*ID', full_text, re.IGNORECASE):
                    mueve_stock = False

            letra = "X"
            match_letra = re.search(r'(?:^|\n)\s*([ABCE])\s*(?:$|\n)', header_text)
            if match_letra: letra = match_letra.group(1)
            elif " A " in header_text: letra = "A"

            datos = {
                "cabecera": {
                    "proveedor": "CROMOSOL", "tipo": tipo, "letra": letra,
                    "fecha": "HOY", "puntoVenta": "0000", "numero": "00000000",
                    "total": "0,00", "percepciones_iibb": [],
                    "mueve_stock": mueve_stock
                },
                "productos": []
            }

            m_f = re.search(r'FECHA:\s*(\d{2}-\d{2}-\d{4})', full_text)
            if m_f: datos["cabecera"]["fecha"] = m_f.group(1).replace('-', '/')
            
            m_n = re.search(r'(\d{4})-(\d{8})', full_text)
            if m_n: 
                datos["cabecera"]["puntoVenta"] = m_n.group(1)
                datos["cabecera"]["numero"] = m_n.group(2)
            else:
                return None, "No se encontró el número de comprobante"

            # --- PIE DE PÁGINA ---
            # --- EXTRACCIÓN DE MONTOS CON RESCATE DE NAN ---
            pie = page.crop((0, page.height * 0.65, page.width, page.height))
            words_pie = pie.extract_words()

            # 1. Intentamos capturar los strings originales
            val_subtotal_str, _ = extraer_valor_por_columna(words_pie, "SUBTOTAL")
            val_descuento_str, _ = extraer_valor_por_columna(words_pie, "DESCUENTO")

            val_neto_str, _ = extraer_valor_por_columna(words_pie, "SUBTOTAL NETO")
            val_iva_str, _ = extraer_valor_por_columna(words_pie, "I.V.A.")
            val_total_str, _ = extraer_valor_por_columna(words_pie, "TOTAL")

            # print(f"DEBUG: Subtotal='{val_subtotal_str}', Neto='{val_neto_str}', IVA='{val_iva_str}', Total='{val_total_str}'")

            # 2. Convertimos a float para operar (nuestro str_to_float ya maneja el "NaN" como 0.0)
            f_subtotal = str_to_float(val_subtotal_str)
            f_descuento = str_to_float(val_descuento_str)
            f_neto = str_to_float(val_neto_str)
            f_iva = str_to_float(val_iva_str)
            f_total = str_to_float(val_total_str)

            # Jerarquía de búsqueda para el Neto
            """
            val_neto_str, _ = extraer_valor_por_columna(words_pie, "NETO")
            
            val_subtotal_str, _ = extraer_valor_por_columna(words_pie, "SUBTOTAL")

            val_iva_str, _ = extraer_valor_por_columna(words_pie, "I.V.A.")
            val_total_str, _ = extraer_valor_por_columna(words_pie, "TOTAL")
            """
            #print(f"DEBUG FINAL: Subtotal='{val_subtotal_str}', Descuento='{val_descuento_str}', Neto='{val_neto_str}', IVA='{val_iva_str}', Total='{val_total_str}'")
            
            # Extraer la cadena de la percepción de IIBB
            val_iibb_str_extracted, jur_iibb = extraer_valor_por_columna(words_pie, "IIBB")
            # Convertir el valor de IIBB a flotante para una comparación numérica precisa
            monto_iibb_float = str_to_float(val_iibb_str_extracted)

            # Solo añadir la percepción si su valor numérico es distinto de cero
            if monto_iibb_float != 0.0:
                 if not jur_iibb: 
                    if "Capital" in [w['text'] for w in words_pie]: jur_iibb = "Capital Federal"
                 datos["cabecera"]["percepciones_iibb"].append({
                    "jurisdiccion": jur_iibb if jur_iibb else "Capital Federal",
                    "monto": float_to_str(monto_iibb_float) # Almacenar en formato canónico
                })
            
            datos["cabecera"]["total"] = val_total_str

            # --- PRODUCTOS Y VALIDACIÓN ---
            words = page.extract_words()
            top_y = 0; bottom_y = page.height
            for w in words:
                if w['text'] == "ARTICULO": top_y = w['top'] - 5
                if "SUBTOTAL" in w['text']: bottom_y = w['top']
            
            if top_y > 0: page_prod = page.crop((0, top_y, page.width, bottom_y))
            else: page_prod = page

            cortes = [10, 46, 88, 460, 535, 600]
            settings = {"vertical_strategy": "explicit", "explicit_vertical_lines": cortes, "horizontal_strategy": "text", "snap_tolerance": 3}
            tabla = page_prod.extract_table(table_settings=settings)

            suma_productos = 0.0
            if tabla:
                for fila in tabla:
                    if not fila or len(fila) < 4: continue
                    if not fila[3] or not re.search(r'\d', fila[3]): continue
                    try:
                        cod = fila[1].replace('\n', '').strip().split(' ')[0]
                        desc = fila[2].replace('\n', ' ').strip()
                        cant_float = float(fila[0].split(',')[0].strip())
                        precio_float = str_to_float(fila[3])
                        
                        linea_total = round(cant_float * precio_float, 2)
                        suma_productos = round(suma_productos + linea_total, 2)

                        datos["productos"].append({
                            "codigo": cod, "descripcion": desc, "cantidad": str(int(cant_float)),
                            "precio": fila[3], "iva": "21.00", "descuento": "0,00"
                        })
                    except Exception as e:
                        print(f"      ⚠️ Advertencia: Error al parsear fila de producto {fila}: {e}")
            #print(datos["productos"]) 
            # --- CHEQUEO TOLERANCIA ---
            diff_prod = abs(suma_productos - f_subtotal)
            
            # Tolerancia dinámica: se añade 0.005 por cada unidad de producto para contemplar el tercer decimal oculto en el PDF
            total_unidades = sum(float(p["cantidad"]) for p in datos["productos"])
            tolerancia_dinamica = TOLERANCIA + (total_unidades * 0.005)
            
            if diff_prod > tolerancia_dinamica:
                msg = f"Error Suma Productos. Calc: {suma_productos} vs Subtotal: {f_subtotal} (Diff: {diff_prod:.2f}, Tol: {tolerancia_dinamica:.2f})"
                return datos, msg # Devolvemos datos para log, pero con mensaje de error

            f_total_leido = str_to_float(val_total_str)
            f_iva = str_to_float(val_iva_str)
            
            # Usar el valor flotante de la percepción de IIBB ya calculado
            total_calc = round(f_subtotal + f_iva + monto_iibb_float, 2)
            diff_total = abs(total_calc - f_total_leido)

            if diff_total > TOLERANCIA:
                msg = f"Error Suma Fiscal. Calc: {total_calc} vs Total PDF: {f_total_leido} (Diff: {diff_total:.2f})"
                return datos, msg

            return datos, None

    except Exception as e:
        return None, f"Excepción de Python: {str(e)}"

def parsear_generico_ia(page, full_text, ruta_pdf):
    """
    Implementación con Google Gemini para facturas desconocidas.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None, "Falta GEMINI_API_KEY en archivo .env"

    try:
        client = genai.Client(api_key=api_key)
        
        # Prompt optimizado para mantener consistencia con el formato de Cromosol
        prompt = f"""
        Analiza el texto de la factura y extrae los datos contables.
        
        Reglas de Formato (CRÍTICO):
        1. Fechas: Formato "DD/MM/AAAA".
        2. Montos: String con formato argentino (ej: "1.500,50"). Usa PUNTO para miles y COMA para decimales.
        3. Tipos: "FACTURA", "NOTA DE CREDITO" o "NOTA DE DEBITO".
        5. Letra: "A", "B", "C" o "M".

        Reglas de Normalización:
        1. PROVEEDOR: Busca el emisor en esta lista: {json.dumps(PROVEEDORES_CONOCIDOS, ensure_ascii=False)}. Si coincide (aunque sea parcial), usa el nombre EXACTO de la lista. Si no, usa la Razón Social del PDF.
        2. PROVINCIAS (IIBB): La 'jurisdiccion' DEBE ser una de estas opciones: {json.dumps(PROVINCIAS_VALIDAS, ensure_ascii=False)}.
           - Ejemplo: Si dice "Cap. Fed." o "CABA", usa "Capital Federal". Si dice "Pcia Bs As", usa "Buenos Aires".

        Texto de la factura:
        {full_text}
        """

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': {
                        "type": "OBJECT",
                        "properties": {
                            "cabecera": {
                                "type": "OBJECT",
                                "properties": {
                                    "proveedor": {"type": "STRING"},
                                    "tipo": {"type": "STRING", "enum": ["FACTURA", "NOTA DE CREDITO", "NOTA DE DEBITO"]},
                                    "letra": {"type": "STRING"},
                                    "fecha": {"type": "STRING"},
                                    "puntoVenta": {"type": "STRING"},
                                    "numero": {"type": "STRING"},
                                    "total": {"type": "STRING"},
                                    "percepciones_iibb": {
                                        "type": "ARRAY",
                                        "items": {
                                            "type": "OBJECT",
                                            "properties": {
                                                "jurisdiccion": {"type": "STRING"},
                                                "monto": {"type": "STRING"}
                                            },
                                            "required": ["jurisdiccion", "monto"]
                                        }
                                    }
                                },
                                "required": ["proveedor", "tipo", "letra", "fecha", "puntoVenta", "numero", "total"]
                            },
                            "productos": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "codigo": {"type": "STRING"},
                                        "descripcion": {"type": "STRING"},
                                        "cantidad": {"type": "STRING"},
                                        "precio": {"type": "STRING"},
                                        "iva": {"type": "STRING"},
                                        "descuento": {"type": "STRING"}
                                    },
                                    "required": ["codigo", "descripcion", "cantidad", "precio"]
                                }
                            }
                        },
                        "required": ["cabecera", "productos"]
                    }
                }
            )
        except Exception as e:
            # Diagnóstico de error 404 (Modelo no encontrado)
            if "404" in str(e) or "NOT_FOUND" in str(e):
                try:
                    print("   ⚠️ Modelo no encontrado. Consultando lista disponible...")
                    # Listar modelos disponibles para esta API Key
                    modelos = [m.name for m in client.models.list()]
                    return None, f"Error 404. Modelos disponibles: {modelos}"
                except Exception as list_err:
                    return None, f"Error 404 y fallo al listar: {list_err}"
            raise e
        
        # Con response_schema, response.text YA es un JSON válido garantizado
        datos = json.loads(response.text)
        
        # Validación básica de estructura
        if "cabecera" not in datos or "productos" not in datos:
            return None, "La IA devolvió un JSON incompleto"
            
        return datos, None

    except Exception as e:
        return None, f"Error IA: {str(e)}"

# ==============================================================================
# 5. DETECTOR Y ORQUESTADOR
# ==============================================================================
def detectar_estrategia(full_text):
    """
    Analiza el texto crudo para decidir qué función usar.
    """
    text_upper = full_text.upper()
    
    # 1. CROMOSOL
    if "CROMOSOL" in text_upper or "30-50072831-7" in text_upper:
        return parsear_cromosol
    
    # 2. AQUÍ AGREGARÍAS OTROS PROVEEDORES
    # if "RAZON SOCIAL OTRO" in text_upper: return parsear_otro

    # 3. FALLBACK A IA (Si no se reconoce ninguno)
    return parsear_generico_ia

def identificar_id_contribuyente(full_text):
    text_clean = full_text.replace("-", "").replace(" ", "")
    # EQUIP STORE S.R.L: CUIT 30719342457
    if "30719342457" in text_clean or "EQUIPSTORE" in text_clean.upper():
        return "1"
    # DE LA PLATA JOSE CARLOS: CUIT 20173327324
    if "20173327324" in text_clean or "DELAPLATAJOSE" in text_clean.upper():
        return "0"
    return None

def procesar_archivo_individual(ruta_pdf):
    """
    Abre el PDF, detecta el proveedor y ejecuta la estrategia correspondiente.
    """
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            if not pdf.pages:
                return None, "El PDF está vacío o no se pudo leer."
            
            page = pdf.pages[0]
            full_text = page.extract_text() or ""
            
            # Selección de Estrategia
            funcion_parser = detectar_estrategia(full_text)
            nombre_parser = funcion_parser.__name__.replace("parsear_", "").upper()
            
            # Ejecución
            parsed_data, parse_error = funcion_parser(page, full_text, ruta_pdf)
            if parsed_data and "cabecera" in parsed_data:
                parsed_data["cabecera"]["archivo"] = os.path.basename(ruta_pdf)
                if "mueve_stock" not in parsed_data["cabecera"]:
                    # Default a mover stock si no fue configurado explícitamente por el parser
                    parsed_data["cabecera"]["mueve_stock"] = True
                
                # Identificar contribuyente
                id_contribuyente = identificar_id_contribuyente(full_text)
                if id_contribuyente is None:
                    return None, "No se pudo identificar un contribuyente válido (CUIT no coincide con JOSE ni EQUIP STORE)", nombre_parser
                parsed_data["cabecera"]["id_contribuyente"] = id_contribuyente
            return parsed_data, parse_error, nombre_parser
            
    except Exception as e:
        return None, f"Error al abrir/leer PDF: {e}", "UNKNOWN"

# ==============================================================================
# 6. EJECUCIÓN DEL LOTE
# ==============================================================================

def ejecutar_lote():
    inicializar_carpetas()
    
    # Cargar la "memoria" del sistema antes de empezar
    cargar_historial_procesado()
    
    archivos = glob.glob(os.path.join(DIR_ENTRADA, "*.[pP][dD][fF]"))
    print(f"\n🚀 Iniciando procesamiento de {len(archivos)} archivos en '{DIR_ENTRADA}'...")
    
    # Usamos ProcessPoolExecutor para procesar en paralelo aprovechando todos los núcleos del CPU
    lote_exitoso = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # Mapeamos la función pesada de parseo en el pool de procesos
        resultados = executor.map(procesar_archivo_individual, archivos)
        
        for ruta, resultado in zip(archivos, resultados):
            nombre = os.path.basename(ruta)
            print(f"\n📄 Analizando: {nombre}")
            
            if resultado is None:
                print("   ❌ Error crítico al procesar el archivo (resultado vacío).")
                mover_archivo(ruta, DIR_SALIDA_ERROR)
                registrar_log(nombre, "?", "?", "?", "FATAL_ERROR", "Resultado nulo")
                continue
                
            datos, error, nombre_parser_usado = resultado
            print(f"   🔎 Estrategia detectada: {nombre_parser_usado}")
            
            prov = datos["cabecera"].get("proveedor", "?") if datos and "cabecera" in datos else "?"
            tipo = datos["cabecera"].get("tipo", "?") if datos and "cabecera" in datos else "?"
            nro = datos["cabecera"].get("numero", "?") if datos and "cabecera" in datos else "?"

            # --- CHEQUEO DE DUPLICADOS HISTÓRICOS ---
            key_actual = f"{prov.strip().upper()}_{tipo.strip().upper()}_{nro.strip()}"
            if key_actual in HISTORIAL_PROCESADO:
                msg = f"Factura ya procesada anteriormente (Historial: {prov} {nro})"
                print(f"   ⏭️ SALTADO: {msg}")
                mover_archivo(ruta, DIR_SALIDA_ERROR) # Movemos a error/descarte para no procesar de nuevo
                registrar_log(nombre, prov, tipo, nro, "YA_PROCESADA", "Detectada en audit_log.csv")
                continue

            if error:
                print(f"   ❌ RECHAZADO: {error}")
                mover_archivo(ruta, DIR_SALIDA_ERROR)
                registrar_log(nombre, prov, tipo, nro, "ERROR", error)
            else:
                print(f"   ✅ APROBADO")
                mover_archivo(ruta, DIR_SALIDA_OK)
                registrar_log(nombre, prov, tipo, nro, "OK", "Procesado correctamente")
                lote_exitoso.append(datos)

    # Guardar JSON Final (Ordenado por id_contribuyente para minimizar cambios de sucursal)
    if lote_exitoso:
        lote_exitoso.sort(key=lambda item: item.get("cabecera", {}).get("id_contribuyente", "0"))
        with open(ARCHIVO_JSON_FINAL, 'w', encoding='utf-8') as f:
            json.dump(lote_exitoso, f, indent=4, ensure_ascii=False)
        print(f"\n✨ Proceso terminado. {len(lote_exitoso)} facturas ordenadas por contribuyente y listas en '{ARCHIVO_JSON_FINAL}'")
    else:
        print("\n⚠️ No se generaron facturas exitosas.")


if __name__ == "__main__":
    ejecutar_lote()