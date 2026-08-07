import os
import re
import pandas as pd
from sqlalchemy.orm import Session
from db.models import Proveedor

def limpiar_cuit(cuit_raw) -> str:
    """Limpia y valida el número de CUIT. Retorna solo números o None si es inválido/vacío."""
    if not cuit_raw or pd.isna(cuit_raw):
        return None
    cuit_clean = re.sub(r'\D', '', str(cuit_raw)).strip()
    if len(cuit_clean) == 11:
        return cuit_clean
    return None

def importar_proveedores_excel(db: Session, excel_path: str) -> dict:
    """
    Importa/actualiza proveedores desde el archivo Excel exportado de Cianbox.
    Mapeo esperado:
    - ID -> id_cianbox
    - Número (CUIT) -> cuit
    - Razón Social -> razon_social
    - Nombre Comercial -> nombre_cianbox / nombre
    """
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"No se encontró el archivo Excel: {excel_path}")

    # Cargar Excel con pandas
    df = pd.read_excel(excel_path)
    
    # Normalizar encabezados en mayúsculas sin espacios extremos
    df.columns = [str(c).strip().upper() for c in df.columns]

    # Buscar columnas dinámicamente por variaciones de nombre
    col_id = next((c for c in df.columns if c in ["ID", "ID_PROVEEDOR", "ID CIANBOX"]), None)
    col_cuit = next((c for c in df.columns if "NÚMERO" in c or "NUMERO" in c or "CUIT" in c), None)
    col_razon = next((c for c in df.columns if "RAZÓN" in c or "RAZON" in c or "SOCIAL" in c), None)
    col_nombre = next((c for c in df.columns if "NOMBRE" in c or "COMERCIAL" in c or "FANTASIA" in c), None)

    if not col_id:
        raise ValueError(f"No se encontró la columna 'ID' en el Excel. Columnas halladas: {list(df.columns)}")

    insertados = 0
    actualizados = 0

    for _, row in df.iterrows():
        id_cian = str(row[col_id]).strip() if pd.notna(row[col_id]) else None
        if not id_cian or id_cian == "nan":
            continue

        cuit = limpiar_cuit(row[col_cuit]) if col_cuit else None
        razon_social = str(row[col_razon]).strip() if col_razon and pd.notna(row[col_razon]) else None
        nombre_comercial = str(row[col_nombre]).strip() if col_nombre and pd.notna(row[col_nombre]) else (razon_social or f"PROVEEDOR_{id_cian}")

        # 1. Prioridad: id_cianbox
        proveedor = db.query(Proveedor).filter_by(id_cianbox=id_cian).first()

        # 2. Prioridad: cuit
        if not proveedor and cuit:
            proveedor = db.query(Proveedor).filter_by(cuit=cuit).first()

        # 3. Prioridad: razon_social
        if not proveedor and razon_social:
            proveedor = db.query(Proveedor).filter(
                (Proveedor.razon_social.ilike(razon_social)) |
                (Proveedor.nombre.ilike(razon_social))
            ).first()

        # 4. Prioridad: nombre comercial / nombre_cianbox
        if not proveedor and nombre_comercial:
            proveedor = db.query(Proveedor).filter(
                (Proveedor.nombre_cianbox.ilike(nombre_comercial)) |
                (Proveedor.nombre.ilike(nombre_comercial))
            ).first()


        if proveedor:

            # Actualizar datos del proveedor homologado
            proveedor.id_cianbox = id_cian
            if cuit: proveedor.cuit = cuit
            if razon_social: proveedor.razon_social = razon_social
            proveedor.nombre_cianbox = nombre_comercial
            proveedor.nombre = nombre_comercial
            actualizados += 1
        else:
            # Insertar nuevo proveedor homologado desde Cianbox
            proveedor = Proveedor(
                id_cianbox=id_cian,
                cuit=cuit,
                razon_social=razon_social or nombre_comercial,
                nombre_cianbox=nombre_comercial,
                nombre=nombre_comercial,
                parser_type="genai"
            )
            db.add(proveedor)
            db.flush()
            insertados += 1

        # 3. Desbloquear facturas en pausa asociadas a este proveedor homologado
        from db.models import Factura
        db.query(Factura).filter_by(
            proveedor_id=proveedor.id,
            estado="REQUIERE_PROVEEDOR_CIANBOX"
        ).update({"estado": "PENDIENTE_CARGA"})

    db.commit()
    print(f"✅ Importación completada desde {os.path.basename(excel_path)}:")
    print(f"   ➕ Nuevos proveedores insertados: {insertados}")
    print(f"   🔄 Proveedores existentes actualizados: {actualizados}")

    return {"insertados": insertados, "actualizados": actualizados}
