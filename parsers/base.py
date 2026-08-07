from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseInvoiceParser(ABC):
    """Clase base abstracta que deben implementar todos los extractores de facturas."""
    
    @abstractmethod
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extrae datos de un archivo PDF de factura.
        
        Devuelve un diccionario estructurado:
        {
            "proveedor": str,
            "cuit_proveedor": str,
            "tipo_comprobante": str,
            "numero_comprobante": str,
            "fecha_emision": str,
            "neto": float,
            "iva": float,
            "percepciones": float,
            "total": float,
            "items": [
                {
                    "codigo": str,
                    "descripcion": str,
                    "cantidad": float,
                    "precio_unitario": float,
                    "subtotal": float
                }
            ]
        }
        """
        pass
