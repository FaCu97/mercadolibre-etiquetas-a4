import os
import glob
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator import CentralOrchestrator

def main():
    folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comprobantes_julio_2026")
    pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
    
    if not pdf_files:
        print(f"No se encontraron archivos PDF en {folder_path}")
        return
        
    print(f"Se encontraron {len(pdf_files)} archivos PDF para procesar.")
    
    orchestrator = CentralOrchestrator()
    ids_procesados = []
    
    for pdf in pdf_files:
        print(f"Procesando archivo: {pdf}")
        try:
            factura = orchestrator.procesar_archivo_especifico(pdf)
            if factura:
                ids_procesados.append(factura.id)
        except Exception as e:
            print(f"Error procesando {pdf}: {e}")
            
    print(f"\nSe extrajo informacion de {len(ids_procesados)} facturas con exito.")
    
    if ids_procesados:
        print("Iniciando carga de las facturas extraidas a Cianbox (Selenium)...")
        try:
            orchestrator.ejecutar_carga_manual(factura_ids=ids_procesados)
            print("Carga completada.")
        except Exception as e:
            print(f"Error durante la carga a Cianbox: {e}")

if __name__ == "__main__":
    main()
