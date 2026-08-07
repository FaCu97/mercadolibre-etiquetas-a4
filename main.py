import os
import sys
import argparse
from datetime import datetime, date

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator import CentralOrchestrator
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

def main():
    parser = argparse.ArgumentParser(description="Orquestador Central de Facturación")
    
    parser.add_argument("--procesar-file", type=str, help="Procesa un archivo PDF específico en el acto")
    parser.add_argument("--importar-proveedores", type=str, help="Importa/actualiza proveedores desde el Excel de Cianbox (ej: --importar-proveedores proveedores.xlsx)")
    parser.add_argument("--cargar-proveedor", type=str, help="Ejecuta la carga nocturna/inmediata filtrada por proveedor")
    parser.add_argument("--cargar-id", type=str, help="Carga facturas por su ID de SQLite (ej: 5 o 5,6,7,8)")
    parser.add_argument("--cargar-ahora", action="store_true", help="Fuerza la ejecución de carga nocturna inmediatamente")
    parser.add_argument("--set-horario", type=str, help="Cambia el horario nocturno en SQL (Formato: HH:MM, ej: 03:30)")

    
    # Nuevos argumentos de filtrado por fecha para descarga de mail
    parser.add_argument("--descargar-rango", action="store_true", help="Descarga e ingesta facturas por rango de fechas")
    parser.add_argument("--desde", type=str, help="Fecha inicio en formato YYYY-MM-DD (ej: 2026-08-01)")
    parser.add_argument("--hasta", type=str, help="Fecha fin en formato YYYY-MM-DD (ej: 2026-08-31)")
    parser.add_argument("--set-fecha-desde", type=str, help="Configura la fecha mínima global en DB para descargar correos")

    args = parser.parse_args()
    orchestrator = CentralOrchestrator()

    if args.importar_proveedores:
        from db.database import SessionLocal
        from services.provider_import_service import importar_proveedores_excel
        db = SessionLocal()
        try:
            importar_proveedores_excel(db, args.importar_proveedores)
        except Exception as e:
            print(f"❌ Error al importar proveedores desde Excel: {e}")
        finally:
            db.close()
        return

    if args.set_fecha_desde:

        try:
            d = datetime.strptime(args.set_fecha_desde, "%Y-%m-%d").date()
            orchestrator.set_config_valor("FECHA_DESDE_MAIL", d.strftime("%Y-%m-%d"))
            print(f"✅ Fecha mínima de mail actualizada en la DB a: {d.strftime('%Y-%m-%d')}")
            return
        except Exception as e:
            print(f"❌ Formato de fecha inválido. Usar YYYY-MM-DD (ej: 2026-08-01). Error: {e}")
            return

    if args.descargar_rango:
        if not args.desde:
            print("❌ Debe especificar --desde YYYY-MM-DD para la descarga por rango.")
            return
        try:
            f_desde = datetime.strptime(args.desde, "%Y-%m-%d").date()
            f_hasta = datetime.strptime(args.hasta, "%Y-%m-%d").date() if args.hasta else date.today()
            print(f"📅 Iniciando descarga e ingesta de correos desde {f_desde} hasta {f_hasta}...")
            orchestrator.descargar_mails_por_rango(f_desde, f_hasta)
            return
        except Exception as e:
            print(f"❌ Error al procesar fechas de rango: {e}")
            return

    if args.set_horario:
        try:
            h, m = args.set_horario.split(":")
            orchestrator.set_config_valor("HORA_CARGA_NOCTURNA", str(int(h)))
            orchestrator.set_config_valor("MINUTO_CARGA_NOCTURNA", str(int(m)))
            print(f"✅ Horario nocturno actualizado en la Base de Datos a las {h.zfill(2)}:{m.zfill(2)} hs.")
            return
        except Exception as e:
            print(f"❌ Formato de horario inválido. Use HH:MM (ej: 03:30). Error: {e}")
            return

    if args.procesar_file:
        orchestrator.procesar_archivo_especifico(args.procesar_file)
        return

    if args.cargar_proveedor:
        orchestrator.ejecutar_carga_manual(proveedor_filtro=args.cargar_proveedor)
        return

    if args.cargar_id:
        try:
            ids = [int(i.strip()) for i in args.cargar_id.split(",") if i.strip()]
            orchestrator.ejecutar_carga_manual(factura_ids=ids)
        except Exception as e:
            print(f"❌ Error procesando IDs: {e}")
        return


    if args.cargar_ahora:
        orchestrator.ejecutar_carga_manual()
        return

    print("==========================================================")
    print("🚀 INICIANDO ORQUESTADOR CENTRAL EN MODO CONTINUO (24/7)")
    print("==========================================================")
    
    orchestrator.start()

    hora = int(orchestrator.get_config_valor("HORA_CARGA_NOCTURNA", "2"))
    minuto = int(orchestrator.get_config_valor("MINUTO_CARGA_NOCTURNA", "0"))

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=orchestrator.ejecutar_carga_manual,
        trigger=CronTrigger(hour=hora, minute=minuto),
        id="carga_nocturna_job",
        name="Carga Nocturna Selenium Cianbox"
    )
    scheduler.start()

    print(f"⏰ Scheduler nocturno activo. Se ejecutará todos los días a las {hora:02d}:{minuto:02d} hs (Configurables en DB).")

    try:
        while True:
            import time
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        orchestrator.stop()
        scheduler.shutdown()
        print("👋 Servidor detenido limpiamente.")

if __name__ == "__main__":
    main()
