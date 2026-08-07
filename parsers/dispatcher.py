import pdfplumber
from parsers.base import BaseInvoiceParser
from parsers.cromosol import CromosolParser

class InvoiceDispatcher:
    """Clase encargada de identificar el proveedor del PDF y seleccionar el parser correspondiente."""
    
    def __init__(self):
        # Parser dedicado determinístico de Cromosol
        self.cromosol_parser = CromosolParser()
        self.parsers = {
            "cromosol": self.cromosol_parser,
            "genai": None  # Se carga bajo demanda
        }
        self._genai_parser = None


    @property
    def genai_parser(self):
        """Carga lazy del parser de Gemini para no fallar si no hay API key o librería en tests simples."""
        if self._genai_parser is None:
            from parsers.genai_parser import GeminiInvoiceParser
            self._genai_parser = GeminiInvoiceParser()
        return self._genai_parser

    def detect_provider(self, pdf_path: str) -> str:
        """Examina las primeras líneas del PDF para identificar el proveedor."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0]
                text = first_page.extract_text() or ""
                
                text_upper = text.upper()
                if "CROMOSOL" in text_upper:
                    return "cromosol"
                
                # A futuro se pueden agregar más proveedores conocidos aquí:
                # if "DISTRIMAR" in text_upper:
                #     return "distrimar"
                
        except Exception as e:
            print(f"⚠️ Error al detectar proveedor en {pdf_path}: {e}")
            
        return "genai"

    def get_parser(self, pdf_path: str) -> BaseInvoiceParser:
        provider_key = self.detect_provider(pdf_path)
        if provider_key == "cromosol":
            return self.cromosol_parser
        else:
            print(f"🤖 [Dispatcher] Proveedor sin parser determinístico. Derivando a Gemini AI...")
            return self.genai_parser
