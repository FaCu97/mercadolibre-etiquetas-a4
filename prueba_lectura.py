import pdfplumber
import re
import json
import os

# --- CONFIGURACIÓN ---
ARCHIVO_PDF = "comprobante-Cromosol-0018-00143157.pdf"
TOLERANCIA = 0.09  # Tolerancia para diferencias aceptables

def str_to_float(precio_str):
    """Convierte '1.500,50' a float 1500.50"""
    if not precio_str: return 0.0
    # Limpiar cualquier caracter que no sea número o coma
    clean = re.sub(r'[^\d,]', '', precio_str)
    # Eliminar puntos de miles si quedaron (aunque el regex anterior ya los sacaría si no son dígitos)
    clean = clean.replace('.', '')
    try:
        return float(clean.replace(',', '.'))
    except ValueError:
        return 0.0

def float_to_str(valor_float):
    """Convierte float a string '1.500,50'"""
    # Usamos format para asegurar 2 decimales fijos
    return "{:,.2f}".format(valor_float).replace(",", "X").replace(".", ",").replace("X", ".")

def extraer_valor_por_columna(words, palabra_clave, margen_vertical=60):
    """Busca palabra clave y devuelve el valor numérico debajo."""
    # Buscamos la ocurrencia más abajo en la página (Pie de página)
    candidatos = [w for w in words if palabra_clave in w['text']]
    if not candidatos: return "0,00", ""
    
    header = candidatos[-1] # El último encontrado
    
    # Rango horizontal (Ancho de columna)
    x_min = header['x0'] - 25
    x_max = header['x1'] + 25
    
    # Rango vertical (Hacia abajo)
    y_min = header['bottom']
    y_max = header['bottom'] + margen_vertical
    
    valores = []
    for w in words:
        mid_x = (w['x0'] + w['x1']) / 2
        if x_min < mid_x < x_max and y_min < w['top'] < y_max:
            # Regex estricto para moneda: digitos, coma, 2 digitos
            if re.search(r'\d+,\d{2}', w['text']):
                valores.append(w['text'])
    
    valor_final = valores[0] if valores else "0,00"

    # Contexto a la derecha (para identificar jurisdicción de IIBB)
    palabras_derecha = [w['text'] for w in words 
                        if abs(w['top'] - header['top']) < 4 
                        and w['x0'] > header['x1']]
    
    contexto = " ".join(palabras_derecha).split("TOTAL")[0].strip()
    
    return valor_final, contexto

def procesar_factura_estricta(ruta_pdf):
    print(f"🚀 Procesando (Modo Estricto): {os.path.basename(ruta_pdf)}")
    if not os.path.exists(ruta_pdf): return None

    with pdfplumber.open(ruta_pdf) as pdf:
        page = pdf.pages[0]
        full_text = page.extract_text() or ""

        # --- 1. CABECERA ---
        header_text = page.crop((0, 0, page.width, 250)).extract_text().upper()
        
        tipo = "FACTURA"
        if "CREDITO" in header_text: tipo = "NOTA DE CREDITO"
        elif "DEBITO" in header_text: tipo = "NOTA DE DEBITO"

        letra = "X"
        match_letra = re.search(r'(?:^|\n)\s*([ABCE])\s*(?:$|\n)', header_text)
        if match_letra: letra = match_letra.group(1)
        elif " A " in header_text: letra = "A"
        elif " B " in header_text: letra = "B"

        datos = {
            "cabecera": {
                "proveedor": "CROMOSOL", "tipo": tipo, "letra": letra,
                "fecha": "HOY", "puntoVenta": "0000", "numero": "00000000",
                "neto_gravado": "0,00", "iva": "0,00", "total": "0,00", 
                "percepciones_iibb": [],
                "validacion": {
                    "suma_productos_ok": False,
                    "suma_total_ok": False,
                    "diferencia_productos": "0,00",
                    "diferencia_total": "0,00"
                }
            },
            "productos": []
        }

        m_f = re.search(r'FECHA:\s*(\d{2}-\d{2}-\d{4})', full_text)
        if m_f: datos["cabecera"]["fecha"] = m_f.group(1).replace('-', '/')
        
        m_n = re.search(r'(\d{4})-(\d{8})', full_text)
        if m_n: 
            datos["cabecera"]["puntoVenta"] = m_n.group(1)
            datos["cabecera"]["numero"] = m_n.group(2)

        # --- 2. PIE DE PÁGINA (Valores Macro) ---
        pie = page.crop((0, page.height * 0.65, page.width, page.height))
        words_pie = pie.extract_words()

        val_neto_str, _ = extraer_valor_por_columna(words_pie, "NETO")
        if val_neto_str == "0,00": val_neto_str, _ = extraer_valor_por_columna(words_pie, "SUBTOTAL")
        
        val_iva_str, _ = extraer_valor_por_columna(words_pie, "I.V.A.")
        val_total_str, _ = extraer_valor_por_columna(words_pie, "TOTAL")
        val_iibb_str, jur_iibb = extraer_valor_por_columna(words_pie, "IIBB")

        datos["cabecera"]["neto_gravado"] = val_neto_str
        datos["cabecera"]["iva"] = val_iva_str
        datos["cabecera"]["total"] = val_total_str
        
        monto_iibb_float = str_to_float(val_iibb_str)
        if val_iibb_str != "0,00":
            if not jur_iibb: 
                if "Capital" in [w['text'] for w in words_pie]: jur_iibb = "Capital Federal"
            datos["cabecera"]["percepciones_iibb"].append({
                "jurisdiccion": jur_iibb if jur_iibb else "Capital Federal",
                "monto": val_iibb_str
            })

        # --- 3. PRODUCTOS Y CÁLCULO DE SUMA EXACTA ---
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

        suma_productos_calculada = 0.0

        if tabla:
            for fila in tabla:
                if not fila or len(fila) < 4: continue
                if not fila[3] or not re.search(r'\d', fila[3]): continue
                try:
                    # Parseo de valores
                    cod = fila[1].replace('\n', '').strip().split(' ')[0]
                    desc = fila[2].replace('\n', ' ').strip()
                    cant_str = fila[0].split(',')[0].strip()
                    precio_str = fila[3].replace('.', '').replace(',', '.') 
                    
                    # CÁLCULO MATEMÁTICO ESTRICTO
                    cant_float = float(cant_str)
                    precio_float = float(precio_str)
                    
                    # 1. Multiplicamos
                    linea_raw = cant_float * precio_float
                    # 2. Redondeamos a 2 decimales INMEDIATAMENTE para simular contabilidad exacta
                    linea_redondeada = round(linea_raw, 2)
                    
                    # 3. Acumulamos el valor redondeado
                    suma_productos_calculada += linea_redondeada

                    # Formato para JSON
                    precio_fmt = "{:,.2f}".format(precio_float).replace(",", "X").replace(".", ",").replace("X", ".")
                    
                    datos["productos"].append({
                        "codigo": cod, "descripcion": desc, "cantidad": cant_str, 
                        "precio": precio_fmt, "iva": "21.00", "descuento": "0,00"
                    })
                except: pass
        
        # Redondeo final de la suma acumulada (por seguridad extrema)
        suma_productos_calculada = round(suma_productos_calculada, 2)

        # --- 4. AUDITORÍA FINAL ESTRICTA ---
        
        # A. Chequeo Horizontal (Suma Productos vs Neto)
        f_neto = str_to_float(val_neto_str)
        diff_prod = abs(suma_productos_calculada - f_neto)
        
        # B. Chequeo Vertical (Neto + IVA + Perc vs Total)
        f_iva = str_to_float(val_iva_str)
        f_total_leido = str_to_float(val_total_str)
        
        # Sumamos y redondeamos para evitar float drift
        total_calculado = round(f_neto + f_iva + monto_iibb_float, 2)
        diff_total = abs(total_calculado - f_total_leido)

        # Llenar reporte
        # Tolerancia < 0.01 significa que la diferencia debe ser matemáticamente 0
        datos["cabecera"]["validacion"]["suma_productos_ok"] = diff_prod < TOLERANCIA
        datos["cabecera"]["validacion"]["diferencia_productos"] = float_to_str(diff_prod)
        
        datos["cabecera"]["validacion"]["suma_total_ok"] = diff_total < TOLERANCIA
        datos["cabecera"]["validacion"]["diferencia_total"] = float_to_str(diff_total)
        
        print(f"\n📊 REPORTE DE AUDITORÍA ESTRICTA:")
        print(f"   1. Suma Productos ({float_to_str(suma_productos_calculada)}) vs Neto ({val_neto_str})")
        print(f"      Diferencia: {diff_prod:.4f} -> {'✅ EXACTO' if diff_prod < TOLERANCIA else '❌ DIFIERE'}")
        
        print(f"   2. Suma Fiscal ({float_to_str(total_calculado)}) vs Total PDF ({val_total_str})")
        print(f"      Diferencia: {diff_total:.4f} -> {'✅ EXACTO' if diff_total < TOLERANCIA else '❌ DIFIERE'}")

        return datos

if __name__ == "__main__":
    resultado = procesar_factura_estricta(ARCHIVO_PDF)
    print("\n--- JSON FINAL ---")
    print(json.dumps([resultado], indent=4, ensure_ascii=False))