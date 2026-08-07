import os
import sys
import time
import signal
from db.database import init_db
from services.config_service import migrar_configuracion_env_a_db
from orchestrator import CentralOrchestrator

def main():
    print("==========================================================")
    print("⚡ INICIANDO SERVICIO: ESCUCHA DE MAIL EN TIEMPO REAL (IDLE)")
    print("==========================================================")

    init_db()
    migrar_configuracion_env_a_db()

    orchestrator = CentralOrchestrator()
    orchestrator.start()

    def signal_handler(sig, frame):
        print("\n🔴 Deteniendo servicio de Mail Listener...")
        orchestrator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        orchestrator.stop()

if __name__ == "__main__":
    main()
