import os
import sys
from datetime import datetime, date

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator import CentralOrchestrator
from db.database import SessionLocal
from db.models import CasillaEmail
from services.invoice_service import InvoiceService
from services.file_utils import obtener_ruta_pdf_unica
from imap_tools import MailBox, A

DIR_COMPROBANTES = os.path.join(os.getcwd(), "comprobantes")
os.makedirs(DIR_COMPROBANTES, exist_ok=True)

def main():
    fecha_desde = date(2026, 7, 29)
    fecha_hasta_exclusiva = date(2026, 9, 2)  # Hasta 1/9 inclusive -> lt 2/9
    
    db: SessionLocal = SessionLocal()
    casillas = db.query(CasillaEmail).filter_by(activa=True).all()
    
    if not casillas:
        print("No hay casillas de correo configuradas.")
        return
        
    ids_procesados = []
    
    for casilla in casillas:
        print(f"\nConectando a {casilla.user} ({casilla.folder})...")
        try:
            with MailBox(casilla.server).login(casilla.user, casilla.password, initial_folder=casilla.folder) as mailbox:
                # Filtrar por fecha y que el sender o subject contenga 'cromosol'
                # imap_tools permite OR logic usando listas o múltiples argumentos, pero buscaremos por 'from'
                # o iteraremos por todos los de la fecha y verificamos sender/subject en python
                query = A(date_gte=fecha_desde, date_lt=fecha_hasta_exclusiva)
                
                db_sess = SessionLocal()
                service = InvoiceService(db_sess)
                
                try:
                    for msg in mailbox.fetch(query):
                        # Filter by sender, subject or attachment name
                        sender = (msg.from_ or "").lower()
                        subject = (msg.subject or "").lower()
                        
                        is_cromosol = "cromosol" in sender or "cromosol" in subject
                        
                        if not is_cromosol:
                            # Let's check attachments names just in case
                            for att in msg.attachments:
                                if "cromosol" in att.filename.lower():
                                    is_cromosol = True
                                    break
                                    
                        if not is_cromosol:
                            continue
                            
                        print(f"Correo de Cromosol encontrado: {subject} ({msg.date_str})")
                        
                        for att in msg.attachments:
                            if att.filename.lower().endswith('.pdf'):
                                pdf_path = obtener_ruta_pdf_unica(DIR_COMPROBANTES, att.filename)
                                with open(pdf_path, 'wb') as f:
                                    f.write(att.payload)
                                    
                                print(f"  -> PDF descargado: {att.filename}")
                                try:
                                    factura = service.process_pdf(pdf_path)
                                    if factura:
                                        ids_procesados.append(factura.id)
                                except Exception as e:
                                    print(f"  -> Error procesando PDF: {e}")
                finally:
                    db_sess.close()
                    
        except Exception as e:
            print(f"Error procesando la casilla {casilla.user}: {e}")
            
    db.close()
    
    print(f"\nSe extrajeron y guardaron {len(ids_procesados)} facturas en total.")
    
    if ids_procesados:
        print("Iniciando carga a Cianbox...")
        orchestrator = CentralOrchestrator()
        orchestrator.ejecutar_carga_manual(factura_ids=ids_procesados)

if __name__ == "__main__":
    main()
