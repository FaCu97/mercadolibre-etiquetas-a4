import os
os.environ["HEADLESS"] = "false"
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Factura
from cargador_selenium import iniciar_driver, login, procesar_lote_desde_sql

engine = create_engine('sqlite:///data/facturas.db')
Session = sessionmaker(bind=engine)
session = Session()

facturas = session.query(Factura).filter(Factura.numero_comprobante.in_(['0034-00000983', '0034-00001453'])).all()

lote_facturas = []
for f in facturas:
    tipo_str = "fc" if "FACTURA" in f.tipo_comprobante else "nc"
    letra_str = f.tipo_comprobante[-1].lower() if len(f.tipo_comprobante) > 0 else "a"
    
    percepciones_list = []
    if f.percepciones and f.percepciones > 0:
        percepciones_list.append({
            "jurisdiccion": "Capital Federal",
            "monto": str(f.percepciones).replace(".", ",")
        })

    lote_facturas.append({
        "_sql_id": f.id,
        "cabecera": {
            "proveedor": f.proveedor.nombre if f.proveedor else "CROMOSOL",
            "id_cianbox": f.proveedor.id_cianbox if (f.proveedor and f.proveedor.id_cianbox) else None,
            "nombre_cianbox": f.proveedor.nombre_cianbox if (f.proveedor and f.proveedor.nombre_cianbox) else (f.proveedor.nombre if f.proveedor else "CROMOSOL"),
            "tipo": tipo_str,
            "letra": letra_str,
            "fecha": f.fecha_emision or "11/09/2026",
            "puntoVenta": f.numero_comprobante.split("-")[0] if "-" in f.numero_comprobante else "0000",
            "numero": f.numero_comprobante.split("-")[1] if "-" in f.numero_comprobante else f.numero_comprobante,
            "total": str(f.total).replace(".", ","),
            "percepciones_iibb": percepciones_list,
            "mueve_stock": f.mueve_stock if f.mueve_stock is not None else True,
            "id_contribuyente": "1" if getattr(f, "cuit_receptor", "") == os.getenv("CUIT_SUCURSAL_1", "30719342457") else "0"
        },
        "productos": [
            {
                "codigo": item.codigo or "",
                "descripcion": item.descripcion,
                "cantidad": str(int(item.cantidad)),
                "precio": str(item.precio_unitario).replace(".", ","),
                "iva": "21.00",
                "descuento": "0,00"
            } for item in f.items
        ]
    })

driver = iniciar_driver()
try:
    login(driver)
    procesar_lote_desde_sql(driver, lote_facturas, session)
finally:
    pass
