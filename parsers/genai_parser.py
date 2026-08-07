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
        "gemini-2.5-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
        "gemini-3.6-flash"
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

        prompt = """
        Sos un experto contable argentino. Analizá esta factura / nota de crédito / nota de débito adjunta en PDF y extraé la información respetando estrictamente el siguiente JSON de salida:

        {
            "proveedor": "NOMBRE O RAZÓN SOCIAL DEL PROVEEDOR EN MAYÚSCULAS",
            "cuit_proveedor": "CUIT del proveedor en formato 20123456789 (solo números)",
            "tipo_comprobante": "FACTURA A" o "NOTA DE CREDITO A" o "FACTURA B" o "NOTA DE CREDITO B" o "FACTURA C",
            "numero_comprobante": "0001-00001234" (formato PuntoDeVenta-Numero de 8 dígitos),
            "fecha_emision": "DD/MM/YYYY",
            "neto": 1234.56 (número float),
            "iva": 259.25 (número float suma de IVA 21%, 10.5%, etc),
            "percepciones": 50.00 (número float de percepciones IIBB/Nacionales),
            "total": 1543.81 (número float total),
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

                # Parsear resultado JSON
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]

                data = json.loads(raw_text.strip())
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
