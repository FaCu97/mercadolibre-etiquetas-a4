import os
import json
import time
from typing import Dict, Any, List
import google.generativeai as genai
from parsers.base import BaseInvoiceParser

from dotenv import load_dotenv

class GeminiInvoiceParser(BaseInvoiceParser):
    """
    Parser universal de facturas utilizando Google Gemini AI.
    Soporta fallback automático en cascada entre modelos Flash-Lite / Flash 
    si se alcanza un límite de cuota (Rate Limit / 429).
    """

    MODELOS_FALLBACK = [
        "models/gemini-3.5-flash",
        "models/gemini-3.5-pro-preview",
        "models/gemini-3.5-flash-lite",
        "models/gemini-3.6-flash",
        "models/gemini-3.1-flash-lite",
    ]

    def __init__(self):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no encontrada en las variables de entorno.")
        genai.configure(api_key=api_key)


    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """Extrae la información estructurada de un PDF enviándolo a la API de Gemini."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"No se encontró el archivo: {pdf_path}")

        print(f"🤖 [Gemini AI] Subiendo PDF a Google AI Studio: {os.path.basename(pdf_path)}...")
        uploaded_file = genai.upload_file(pdf_path)

        cuit_eq = os.getenv("CUIT_SUCURSAL_1", "30719342457")
        cuit_jo = os.getenv("CUIT_SUCURSAL_0", "20173327324")

        prompt = """
        Sos un experto contable argentino. Analizá esta factura / nota de crédito / nota de débito adjunta en PDF y extraé la información respetando estrictamente el siguiente JSON de salida:

        {
            "proveedor": "NOMBRE O RAZÓN SOCIAL DEL PROVEEDOR EN MAYÚSCULAS",
            "cuit_proveedor": "CUIT del proveedor en formato 20123456789 (solo números)",
            "cuit_receptor": "CUIT del receptor/comprador de la factura en formato 20123456789 (solo números. Ej: CUIT_EQ o CUIT_JO)",
            "tipo_comprobante": "FACTURA A" o "NOTA DE CREDITO A" o "FACTURA B" o "NOTA DE CREDITO B" o "FACTURA C",
            "numero_comprobante": "0001-00001234" (formato PuntoDeVenta-Numero de 8 dígitos),
            "fecha_emision": "DD/MM/YYYY",
            "neto": 1234.56 (número float),
            "iva": 259.25 (número float suma de IVA 21%, 10.5%, etc),
            "percepciones_iibb": [
                {
                    "jurisdiccion": "Nombre de la provincia o entidad (ej: Capital Federal)",
                    "monto": 50.00
                }
                // Puede haber varios objetos en la lista
            ],
            "total": 1543.81 (número float total),
            "mueve_stock": true (boolean: poner false si es una NOTA DE CRÉDITO financiera por volumen, oferta, arreglo, DROPSHIPPING, descuento comercial o de ajuste sin devolución de mercadería física. Poner true para Facturas, Notas de Débito o Notas de Crédito por devolución física de artículos),

            "items": [

                {
                    "codigo": "COD123" (código de producto/artículo),
                    "descripcion": "Descripción del ítem o servicio",
                    "cantidad": 2.0 (float),
                    "precio_unitario": 617.28 (float),
                    "subtotal": 1234.56 (float)
                }
            ]
        }

        Respuestas únicamente en JSON puro, sin bloques markdown extra de comillas inversas ```json.
        """
        prompt = prompt.replace("CUIT_EQ", cuit_eq).replace("CUIT_JO", cuit_jo)

        # Intentar llamada con la lista de modelos (Rotación automática ante Rate Limit / 429)
        for model_name in self.MODELOS_FALLBACK:
            try:
                print(f"📡 Invocando modelo Gemini: {model_name}...")
                model = genai.GenerativeModel(model_name)
                
                # Configuración para forzar salida JSON estructurada
                response = model.generate_content(
                    [uploaded_file, prompt],
                    generation_config={"response_mime_type": "application/json"}
                )

                # Limpieza de archivo subido a Google Cloud
                try:
                    uploaded_file.delete()
                except Exception:
                    pass

                # Parsear resultado JSON de forma robusta
                raw_text = response.text.strip()
                # Eliminar posibles fences markdown
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                # Extraer el bloque JSON principal
                def _extract_json(txt: str) -> str:
                    start = txt.find("{")
                    end = txt.rfind("}")
                    if start != -1 and end != -1 and end > start:
                        return txt[start:end+1]
                    raise ValueError("No se encontró objeto JSON en la respuesta")
                try:
                    json_str = _extract_json(raw_text)
                    data = json.loads(json_str)
                except Exception as parse_err:
                    print(f"⚠️ Error al parsear respuesta Gemini: {parse_err}")
                    raise
                # If detailed IIBB perceptions are present, compute total amount for backward compatibility
                if "percepciones_iibb" in data:
                    data["percepciones"] = sum(item.get("monto", 0) for item in data["percepciones_iibb"])
                print(f"✅ [Gemini AI - {model_name}] Extraídos datos de {data.get('proveedor')} (Comp: {data.get('numero_comprobante')})")
                return data

            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "quota" in err_msg or "rate limit" in err_msg or "resource_exhausted" in err_msg:
                    print(f"⚠️ Límite de cuota (RPM/RPD) alcanzado en {model_name}. Rotando al siguiente modelo...")
                    time.sleep(1.5)  # Pausa antes del rotado
                    continue
                else:
                    # Si es otro error de red o lectura
                    try:
                        uploaded_file.delete()
                    except:
                        pass
                    raise Exception(f"Error procesando PDF con Gemini ({model_name}): {e}")

        # Si todos los modelos de la lista agotaron su cuota
        try:
            uploaded_file.delete()
        except:
            pass
        raise Exception("❌ Todos los modelos de Gemini han alcanzado su límite de cuota diario/minuto.")

# Helper for one‑liner execution (network‑enabled)
def process_with_network(pdf_path: str) -> dict:
    """Convenient wrapper that creates a parser instance and calls ``extract``.
    Use it from the command line with ``BypassSandbox:true`` so the script can
    reach the Gemini API.
    """
    parser = GeminiInvoiceParser()
    return parser.extract(pdf_path)
