import os
import time
import threading
from datetime import datetime, date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from db.database import SessionLocal, init_db
from db.models import Factura, Proveedor, CasillaEmail, ConfiguracionSistema
from services.invoice_service import InvoiceService
from services.config_service import migrar_configuracion_env_a_db
from services.file_utils import obtener_ruta_pdf_unica
from imap_tools import MailBox, A, MailMessageFlags


DIR_COMPROBANTES = os.path.join(os.getcwd(), "comprobantes")



class CentralOrchestrator:
    def __init__(self):
        init_db()
        migrar_configuracion_env_a_db()
        os.makedirs(DIR_COMPROBANTES, exist_ok=True)

        self.running = False
        self._idle_threads: List[threading.Thread] = []

    def get_config_valor(self, clave: str, default: str) -> str:
        db: Session = SessionLocal()
        try:
            conf = db.query(ConfiguracionSistema).filter_by(clave=clave).first()
            return conf.valor if conf else default
        finally:
            db.close()

    def set_config_valor(self, clave: str, valor: str):
        db: Session = SessionLocal()
        try:
            conf = db.query(ConfiguracionSistema).filter_by(clave=clave).first()
            if conf:
                conf.valor = str(valor)
            else:
                conf = ConfiguracionSistema(clave=clave, valor=str(valor))
                db.add(conf)
            db.commit()
            print(f"⚙️ Configuración actualizada en SQL: {clave} = {valor}")
        finally:
            db.close()

    def procesar_archivo_especifico(self, pdf_path: str) -> Factura:
        """Procesa manualmente un archivo PDF concreto."""
        db: Session = SessionLocal()
        try:
            service = InvoiceService(db)
            print(f"🎯 [Orquestador] Procesando archivo específico: {pdf_path}")
            return service.process_pdf(pdf_path)
        finally:
            db.close()

    def ejecutar_carga_manual(self, proveedor_filtro: Optional[str] = None, factura_id: Optional[int] = None, factura_ids: Optional[List[int]] = None):
        """Ejecuta la carga Selenium bajo demanda, opcionalmente filtrada."""
        print(f"🚀 [Orquestador] Ejecutando carga manual/bajo demanda... (Filtro Prov: {proveedor_filtro}, IDs: {factura_ids or factura_id})")
        try:
            from cargador_selenium import cargar_facturas_cianbox
            cargar_facturas_cianbox(proveedor_filtro=proveedor_filtro, factura_id=factura_id, factura_ids=factura_ids)
        except Exception as e:
            print(f"⚠️ Nota de ejecución Selenium: {e}")


    def descargar_mails_por_rango(self, fecha_desde: date, fecha_hasta: date):
        db: Session = SessionLocal()
        casillas = db.query(CasillaEmail).filter_by(activa=True).all()
        db.close()

        if not casillas:
            print("⚠️ No hay casillas de correo activas configuradas en la Base de Datos.")
            return

        fecha_hasta_exclusivo = fecha_hasta + timedelta(days=1)

        for casilla in casillas:
            print(f"🔍 [Mail Rango] Conectando a {casilla.user} ({casilla.folder}) | Desde: {fecha_desde} Hasta: {fecha_hasta}...")
            try:
                with MailBox(casilla.server).login(casilla.user, casilla.password, initial_folder=casilla.folder) as mailbox:
                    query = A(date_gte=fecha_desde, date_lt=fecha_hasta_exclusivo)
                    
                    db_sess = SessionLocal()
                    service = InvoiceService(db_sess)
                    descargados = 0

                    try:
                        for msg in mailbox.fetch(query):
                            for att in msg.attachments:
                                if att.filename.lower().endswith('.pdf'):
                                    pdf_path = obtener_ruta_pdf_unica(DIR_COMPROBANTES, att.filename)


                                    with open(pdf_path, 'wb') as f:
                                        f.write(att.payload)
                                    print(f"  📥 PDF descargado ({msg.date_str}): {att.filename}")
                                    service.process_pdf(pdf_path)
                                    descargados += 1
                    finally:
                        db_sess.close()

                    print(f"✅ Finalizado {casilla.user}: {descargados} facturas procesadas en el rango.")

            except Exception as e:
                print(f"❌ Error descargando rango para {casilla.user}: {e}")

    def _escuchar_casilla_idle(self, casilla_id: int):
        while self.running:
            db: Session = SessionLocal()
            casilla = db.query(CasillaEmail).get(casilla_id)
            db.close()

            if not casilla or not casilla.activa:
                break

            print(f"⚡ [IMAP IDLE] Conectando a {casilla.server} ({casilla.user}) [{casilla.folder}]...")

            try:
                with MailBox(casilla.server).login(casilla.user, casilla.password, initial_folder=casilla.folder) as mailbox:
                    print(f"📡 [IMAP IDLE] Escuchando en tiempo real: {casilla.user}")
                    
                    while self.running:
                        responses = mailbox.idle.wait(timeout=29 * 60)
                        if responses:
                            print(f"📩 [Mail Push] Evento recibido en {casilla.user} a las {datetime.now().strftime('%H:%M:%S')}")
                            self._descargar_y_procesar_mails(mailbox)

            except Exception as e:
                print(f"⚠️ [IMAP IDLE] Error en {casilla.user}: {e}. Reintentando en 15 seg...")
                time.sleep(15)

    def _descargar_y_procesar_mails(self, mailbox: MailBox):
        db: Session = SessionLocal()
        service = InvoiceService(db)
        try:
            fecha_min_str = self.get_config_valor("FECHA_DESDE_MAIL", None)
            if fecha_min_str:
                f_desde = datetime.strptime(fecha_min_str, "%Y-%m-%d").date()
                query = A(seen=False, date_gte=f_desde)
            else:
                query = A(seen=False)

            for msg in mailbox.fetch(query):
                for att in msg.attachments:
                    if att.filename.lower().endswith('.pdf'):
                        pdf_path = obtener_ruta_pdf_unica(DIR_COMPROBANTES, att.filename)


                        with open(pdf_path, 'wb') as f:
                            f.write(att.payload)
                        print(f"📥 PDF guardado: {att.filename}")
                        service.process_pdf(pdf_path)
                mailbox.flag(msg.uid, [MailMessageFlags.SEEN], True)
        finally:
            db.close()

    def start(self):
        self.running = True
        print(f"🟢 [Orquestador Central] Servidor iniciado.")

        hora = self.get_config_valor("HORA_CARGA_NOCTURNA", "2")
        minuto = self.get_config_valor("MINUTO_CARGA_NOCTURNA", "0")
        print(f"⏰ Horario nocturno SQL: {hora.zfill(2)}:{minuto.zfill(2)} hs.")

        db: Session = SessionLocal()
        casillas = db.query(CasillaEmail).filter_by(activa=True).all()
        db.close()

        print(f"📧 Se encontraron {len(casillas)} casillas de e-mail activas en la Base de Datos.")

        for c in casillas:
            t = threading.Thread(target=self._escuchar_casilla_idle, args=(c.id,), daemon=True)
            t.start()
            self._idle_threads.append(t)

    def stop(self):
        self.running = False
        print("🔴 Deteniendo orquestador...")
