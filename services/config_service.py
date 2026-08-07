import os
from sqlalchemy.orm import Session
from db.database import SessionLocal, init_db
from db.models import CasillaEmail, ConfiguracionSistema

def migrar_configuracion_env_a_db():
    """
    Migra las variables de entorno (.env) a la Base de Datos SQLite
    para que se puedan administrar dinámicamente sin reiniciar el servidor.
    """
    init_db()
    db: Session = SessionLocal()
    
    try:
        # 1. Configuración de Horario Nocturno
        hora_env = os.getenv("HORA_CARGA_NOCTURNA", "2")
        minuto_env = os.getenv("MINUTO_CARGA_NOCTURNA", "0")
        
        configs_iniciales = [
            ("HORA_CARGA_NOCTURNA", hora_env, "Hora del día (0-23) para ejecutar la carga Selenium"),
            ("MINUTO_CARGA_NOCTURNA", minuto_env, "Minuto del día (0-59) para ejecutar la carga Selenium"),
            ("TOLERANCIA_VALOR", "0.09", "Tolerancia en pesos para errores de redondeo")
        ]

        for clave, valor, desc in configs_iniciales:
            conf = db.query(ConfiguracionSistema).filter_by(clave=clave).first()
            if not conf:
                conf = ConfiguracionSistema(clave=clave, valor=valor, descripcion=desc)
                db.add(conf)
                print(f"⚙️ Configuración SQLite agregada: {clave} = {valor}")

        # 2. Casillas de Correo
        # Revisa EMAIL_USER_1, EMAIL_USER_2... o EMAIL_USER legacy
        index = 1
        cuentas_encontradas = 0

        while True:
            user = os.getenv(f"EMAIL_USER_{index}") or (os.getenv("EMAIL_USER") if index == 1 else None)
            pwd = os.getenv(f"EMAIL_PASS_{index}") or (os.getenv("EMAIL_PASS") if index == 1 else None)
            folder = os.getenv(f"EMAIL_FOLDER_{index}") or (os.getenv("EMAIL_FOLDER", "INBOX") if index == 1 else "INBOX")
            server = os.getenv("EMAIL_SERVER", "imap.gmail.com")

            if not user and not pwd:
                break

            if user and pwd:
                casilla = db.query(CasillaEmail).filter_by(user=user).first()
                if not casilla:
                    casilla = CasillaEmail(
                        nombre=f"Casilla {index} ({user})",
                        server=server,
                        user=user,
                        password=pwd,
                        folder=folder,
                        activa=True
                    )
                    db.add(casilla)
                    cuentas_encontradas += 1
                    print(f"📧 Casilla de mail agregada a SQLite: {user} [{folder}]")

            index += 1
            if os.getenv("EMAIL_USER") and index > 1:
                break  # Si era legacy, cortar en la primera

        db.commit()
        print(f"✅ Migración inicial a SQLite completada ({cuentas_encontradas} casillas de correo).")

    except Exception as e:
        db.rollback()
        print(f"❌ Error al migrar configuración a la Base de Datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrar_configuracion_env_a_db()
