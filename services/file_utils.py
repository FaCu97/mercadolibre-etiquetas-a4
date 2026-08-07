import os
from datetime import datetime

def obtener_ruta_pdf_unica(dir_base: str, filename_original: str) -> str:
    """
    Garantiza que el archivo PDF no sobrescriba a uno existente con el mismo nombre.
    Si ya existe 'Factura.pdf', retorna 'Factura_20260806_233000_1.pdf'.
    """
    nombre_base, ext = os.path.splitext(filename_original)
    ruta_target = os.path.join(dir_base, filename_original)

    if not os.path.exists(ruta_target):
        return ruta_target

    contador = 1
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    while os.path.exists(ruta_target):
        nuevo_nombre = f"{nombre_base}_{timestamp}_{contador}{ext}"
        ruta_target = os.path.join(dir_base, nuevo_nombre)
        contador += 1

    return ruta_target
