import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from db.models import Factura
from cargador_selenium import cargar_facturas_cianbox

# Ejecutar visualmente para que veas el proceso (podés cambiarlo a "true" si preferís que corra oculto)
os.environ["HEADLESS"] = "false"

# 1. Conectar a la base de datos
engine = create_engine('sqlite:///data/facturas.db')
Session = sessionmaker(bind=engine)
session = Session()

# 2. Identificar las 26 facturas de EQUIP STORE SRL
facturas = session.query(Factura).filter(Factura.cuit_receptor == '30719342457').all()
factura_ids = []

for f in facturas:
    # Las marcamos nuevamente como pendientes para que el script las tome
    f.estado = "PENDIENTE_CARGA"
    factura_ids.append(f.id)

session.commit()
session.close()

print(f"✅ Se resetearon {len(factura_ids)} comprobantes de EQUIP STORE SRL.")
print("🚀 Lanzando Selenium (Cianbox)...")

# 3. Lanzar la carga usando la función principal pero acotada a esos IDs
cargar_facturas_cianbox(factura_ids=factura_ids)
