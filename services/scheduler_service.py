import os
import sys
import time
from db.database import SessionLocal, init_db
from db.models import ConfiguracionSistema
from orchestrator import CentralOrchestrator
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

def get_horario_db():
    db = SessionLocal()
    try:
        h = db.query(ConfiguracionSistema).filter_by(clave="HORA_CARGA_NOCTURNA").first()
        m = db.query(ConfiguracionSistema).filter_by(clave="MINUTO_CARGA_NOCTURNA").first()
        hora = int(h.valor) if h else 2
        minuto = int(m.valor) if m else 0
        return hora, minuto
    finally:
        db.close()

def main():
    print("==========================================================")
    print("⏰ INICIANDO SERVICIO: SCHEDULER DE CARGA NOCTURNA")
    print("==========================================================")

    init_db()
    orchestrator = CentralOrchestrator()

    hora, minuto = get_horario_db()

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=orchestrator.ejecutar_carga_manual,
        trigger=CronTrigger(hour=hora, minute=minuto),
        id="carga_nocturna_job",
        name="Carga Nocturna Selenium Cianbox"
    )
    scheduler.start()

    print(f"⏰ Scheduler activo. Carga nocturna programada a las {hora:02d}:{minuto:02d} hs (Datos desde SQLite).")

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("👋 Scheduler detenido.")

if __name__ == "__main__":
    main()
