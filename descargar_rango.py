import os
import sys
from datetime import date

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from orchestrator import CentralOrchestrator

def main():
    orchestrator = CentralOrchestrator()
    fecha_desde = date(2026, 8, 29)
    fecha_hasta = date(2026, 10, 2)
    orchestrator.descargar_mails_por_rango(fecha_desde, fecha_hasta)
    print("Descarga completada.")

if __name__ == "__main__":
    main()
