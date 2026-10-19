import os
import re
import pdfplumber
from typing import Dict, Any, Tuple
from parsers.base import BaseInvoiceParser

TOLERANCIA = 0.09

def str_to_float(precio_str: str) -> float:
    if not precio_str:
        return 0.0
    clean = re.sub(r'[^\d,]', '', precio_str).replace('.', '')
    try:
        return float(clean.replace(',', '.'))
    except ValueError:
        return 0.0

def float_to_str(valor_float: float) -> str:
    return "{:,.2f}".format(round(valor_float, 2)).replace(",", "X").replace(".", ",").replace("X", ".")

def obtener_valor_debajo_de_header(words: list, header: dict, margen_vertical: int = 60) -> Tuple[str, str]:
    x_centro_header = (header['x0'] + header['x1']) / 2
    
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

def extraer_valor_por_columna(words: list, palabra_clave: str, margen_vertical: int = 60) -> Tuple[str, str]:
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
                
    candidatos = [w for w in words if w['text'].strip().upper() == palabra_clave]
    if not candidatos:
        candidatos = [w for w in words if palabra_clave in w['text'].upper()]
        if palabra_clave == "TOTAL":
            candidatos = [w for w in candidatos if "SUBTOTAL" not in w['text'].upper()]
            
    if not candidatos:
        return "0,00", ""
    
    if palabra_clave == "SUBTOTAL" and len(candidatos) > 1:
        header = candidatos[0]
    else:
        header = candidatos[-1]
        
    return obtener_valor_debajo_de_header(words, header, margen_vertical)


class CromosolParser(BaseInvoiceParser):
    """Extractor específico para facturas de Cromosol utilizando pdfplumber."""
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            full_text = page.extract_text() or ""
            
            # 1. Cabecera
            header_text = page.crop((0, 0, page.width, 250)).extract_text().upper()
            if "CREDITO" in header_text:
                tipo = "NOTA DE CREDITO"
            elif "DEBITO" in header_text:
                tipo = "NOTA DE DEBITO"
            else:
                tipo = "FACTURA"

            mueve_stock = True
            if tipo == "NOTA DE CREDITO":
                if re.search(r'POR:\s*(VOLUMEN|OFERTA|OPERACI[OÓ]N|ARREGLO|DROPSHIPPING)|(VOLUMEN|OFERTA|OPERACI[OÓ]N|ARREGLO|DROPSHIPPING)\s*ID|DROPSHIPPING', full_text, re.IGNORECASE):
                    mueve_stock = False


            letra = "A"
            match_letra = re.search(r'(?:^|\n)\s*([ABCE])\s*(?:$|\n)', header_text)
            if match_letra:
                letra = match_letra.group(1)

            fecha = ""
            m_f = re.search(r'FECHA:\s*(\d{2}-\d{2}-\d{4})', full_text)
            if m_f:
                fecha = m_f.group(1).replace('-', '/')
                
            cuit_receptor = ""
            # Buscar el CUIT del receptor (distinto al de CROMOSOL)
            cuits_completos = re.findall(r'\b(?:20|23|24|27|30|33)-?\d{8}-?\d\b', full_text)
            for c in cuits_completos:
                c_clean = c.replace("-", "")
                if c_clean != "30500728317":
                    cuit_receptor = c_clean
                    break
            
            punto_venta, numero = "0000", "00000000"
            m_n = re.search(r'(\d{4})-(\d{8})', full_text)
            if m_n: 
                punto_venta = m_n.group(1)
                numero = m_n.group(2)
            else:
                raise ValueError("No se encontró el número de comprobante")

            # 2. Pie de Página (Montos y Percepciones)
            pie = page.crop((0, page.height * 0.65, page.width, page.height))
            words_pie = pie.extract_words()

            val_subtotal_str, _ = extraer_valor_por_columna(words_pie, "SUBTOTAL")
            val_neto_str, _ = extraer_valor_por_columna(words_pie, "SUBTOTAL NETO")
            val_iva_str, _ = extraer_valor_por_columna(words_pie, "I.V.A.")
            val_total_str, _ = extraer_valor_por_columna(words_pie, "TOTAL")

            f_subtotal = str_to_float(val_subtotal_str)
            f_neto = str_to_float(val_neto_str) or f_subtotal
            f_iva = str_to_float(val_iva_str)
            f_total_leido = str_to_float(val_total_str)

            val_iibb_str_extracted, jur_iibb = extraer_valor_por_columna(words_pie, "IIBB")
            monto_iibb_float = str_to_float(val_iibb_str_extracted)

            percepciones_list = []
            if monto_iibb_float != 0.0:
                if not jur_iibb:
                    if "Capital" in [w['text'] for w in words_pie]:
                        jur_iibb = "Capital Federal"
                percepciones_list.append({
                    "jurisdiccion": jur_iibb if jur_iibb else "Capital Federal",
                    "monto": float_to_str(monto_iibb_float)
                })

            # 3. Productos / Ítems
            words = page.extract_words()
            top_y = 0; bottom_y = page.height
            for w in words:
                if w['text'] == "ARTICULO":
                    top_y = w['top'] - 5
                if "SUBTOTAL" in w['text']:
                    bottom_y = w['top']
            
            if top_y > 0:
                page_prod = page.crop((0, top_y, page.width, bottom_y))
            else:
                page_prod = page

            cortes = [10, 46, 88, 460, 535, 600]
            settings = {
                "vertical_strategy": "explicit",
                "explicit_vertical_lines": cortes,
                "horizontal_strategy": "text",
                "snap_tolerance": 3
            }
            tabla = page_prod.extract_table(table_settings=settings)

            items = []
            suma_productos = 0.0
            if tabla:
                for fila in tabla:
                    if not fila or len(fila) < 4:
                        continue
                    if not fila[3] or not re.search(r'\d', fila[3]):
                        continue
                    try:
                        cod = fila[1].replace('\n', '').strip().split(' ')[0]
                        desc = fila[2].replace('\n', ' ').strip()
                        cant_float = float(fila[0].split(',')[0].strip())
                        precio_float = str_to_float(fila[3])
                        
                        linea_total = round(cant_float * precio_float, 2)
                        suma_productos = round(suma_productos + linea_total, 2)

                        items.append({
                            "codigo": cod,
                            "descripcion": desc,
                            "cantidad": cant_float,
                            "precio_unitario": precio_float,
                            "subtotal": linea_total
                        })
                    except Exception as e:
                        print(f"⚠️ Advertencia al parsear producto {fila}: {e}")

            # 4. Validaciones contables
            diff_prod = abs(suma_productos - f_subtotal)
            total_unidades = sum(p["cantidad"] for p in items)
            tolerancia_dinamica = TOLERANCIA + (total_unidades * 0.005)
            
            if diff_prod > tolerancia_dinamica:
                raise ValueError(f"Error Suma Productos. Calc: {suma_productos} vs Subtotal: {f_subtotal} (Diff: {diff_prod:.2f})")

            total_calc = round(f_subtotal + f_iva + monto_iibb_float, 2)
            diff_total = abs(total_calc - f_total_leido)
            if diff_total > TOLERANCIA:
                raise ValueError(f"Error Suma Fiscal. Calc: {total_calc} vs Total PDF: {f_total_leido} (Diff: {diff_total:.2f})")

            # Retorno de datos estandarizados
            return {
                "proveedor": "CROMOSOL",
                "cuit_proveedor": "30500728317",
                "cuit_receptor": cuit_receptor,
                "tipo_comprobante": f"{tipo} {letra}",
                "numero_comprobante": f"{punto_venta}-{numero}",
                "fecha_emision": fecha,
                "neto": f_neto,
                "iva": f_iva,
                "percepciones": monto_iibb_float,
                "total": f_total_leido,
                "percepciones_list": percepciones_list,
                "mueve_stock": mueve_stock,
                "items": items
            }

