import os
from sqlalchemy.orm import Session
from db.models import Proveedor, Factura, FacturaItem, ProcesoLog
from parsers.dispatcher import InvoiceDispatcher
from datetime import datetime

class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.dispatcher = InvoiceDispatcher()

    def process_pdf(self, pdf_path: str) -> Factura:
        """
        Procesa un archivo PDF:
        1. Detecta proveedor y selecciona parser.
        2. Extrae los datos del PDF.
        3. Persiste en SQLite (Proveedor, Factura, Ítems y Log).
        """
        archivo_nombre = os.path.basename(pdf_path)
        
        try:
            parser = self.dispatcher.get_parser(pdf_path)
            datos = parser.extract(pdf_path)
            
            # Buscar únicamente proveedores PREVIAMENTE HOMOLOGADOS en SQLite (con id_cianbox o CUIT registrado)
            prov_cuit = str(datos.get("cuit_proveedor", "")).replace("-", "").strip()
            prov_nombre = datos.get("proveedor", "CROMOSOL").upper()
            
            proveedor = None
            if prov_cuit:
                proveedor = self.db.query(Proveedor).filter_by(cuit=prov_cuit).first()

            if not proveedor and prov_nombre:
                # 2. Razón Social
                proveedor = self.db.query(Proveedor).filter(
                    (Proveedor.razon_social.ilike(prov_nombre)) |
                    (Proveedor.nombre.ilike(prov_nombre))
                ).first()

            if not proveedor and prov_nombre:
                # 3. Nombre comercial / nombre_cianbox
                proveedor = self.db.query(Proveedor).filter(
                    (Proveedor.nombre_cianbox.ilike(prov_nombre))
                ).first()


            # REGLA DE NEGOCIO: Si el proveedor NO está homologado en Cianbox, la factura queda pausada
            requiere_homologacion = False
            if not proveedor or not proveedor.id_cianbox:
                requiere_homologacion = True
                if not proveedor:
                    # Se crea como registro preliminar no homologado
                    proveedor = Proveedor(
                        nombre=prov_nombre,
                        cuit=prov_cuit or None,
                        nombre_cianbox=prov_nombre,
                        razon_social=prov_nombre,
                        id_cianbox=None,  # Sin ID Cianbox -> No homologado
                        parser_type="genai"
                    )
                    self.db.add(proveedor)
                    self.db.commit()
                    self.db.refresh(proveedor)

            # Estado de carga: PENDIENTE_CARGA (si está homologado) vs REQUIERE_PROVEEDOR_CIANBOX (si falta alta en Cianbox)
            estado_inicial = "REQUIERE_PROVEEDOR_CIANBOX" if requiere_homologacion else "PENDIENTE_CARGA"



            # Verificar si la factura ya existe
            num_comp = datos["numero_comprobante"]
            factura_existente = self.db.query(Factura).filter_by(
                proveedor_id=proveedor.id,
                numero_comprobante=num_comp
            ).first()

            if factura_existente:
                print(f"ℹ️ La factura {num_comp} de {prov_nombre} ya está en la Base de Datos. Registrando intento de re-ingreso...")
                log_dup = ProcesoLog(
                    factura_id=factura_existente.id,
                    nivel="WARNING",
                    mensaje=f"Intento de re-ingreso o adjunto duplicado recibido ({archivo_nombre}). Conservado en disco."
                )
                self.db.add(log_dup)
                self.db.commit()
                return factura_existente


            # Crear registro de Factura


            factura = Factura(
                proveedor_id=proveedor.id,
                numero_comprobante=num_comp,
                tipo_comprobante=datos["tipo_comprobante"],
                fecha_emision=datos.get("fecha_emision"),
                neto=datos["neto"],
                iva=datos["iva"],
                percepciones=datos["percepciones"],
                total=datos["total"],
                archivo_pdf_path=pdf_path,
                archivo_nombre=archivo_nombre,
                estado=estado_inicial,
                fecha_procesamiento=datetime.utcnow()
            )
            self.db.add(factura)
            self.db.commit()
            self.db.refresh(factura)

            if requiere_homologacion:
                print(f"⚠️ Factura {num_comp} pausada: El proveedor '{prov_nombre}' (CUIT: {prov_cuit or 'S/N'}) no está homologado en Cianbox. Estado: REQUIERE_PROVEEDOR_CIANBOX")


            # Insertar Ítems
            for item in datos.get("items", []):
                db_item = FacturaItem(
                    factura_id=factura.id,
                    codigo=item.get("codigo"),
                    descripcion=item["descripcion"],
                    cantidad=item["cantidad"],
                    precio_unitario=item["precio_unitario"],
                    subtotal=item["subtotal"]
                )
                self.db.add(db_item)

            # Log de éxito
            log = ProcesoLog(
                factura_id=factura.id,
                nivel="INFO",
                mensaje=f"Factura {num_comp} procesada y validada correctamente."
            )
            self.db.add(log)
            self.db.commit()

            print(f"✅ Factura {num_comp} procesada y guardada en SQLite (ID: {factura.id})")
            return factura

        except Exception as e:
            self.db.rollback()
            error_msg = f"Error al procesar {archivo_nombre}: {str(e)}"
            print(f"❌ {error_msg}")
            
            # Guardar registro de error
            factura_error = Factura(
                numero_comprobante=archivo_nombre,
                tipo_comprobante="DESCONOCIDO",
                archivo_pdf_path=pdf_path,
                archivo_nombre=archivo_nombre,
                estado="ERROR_PROCESAMIENTO",
                motivo_error=str(e),
                fecha_procesamiento=datetime.utcnow()
            )
            self.db.add(factura_error)
            self.db.commit()
            self.db.refresh(factura_error)

            log_error = ProcesoLog(
                factura_id=factura_error.id,
                nivel="ERROR",
                mensaje=error_msg
            )
            self.db.add(log_error)
            self.db.commit()

            return factura_error
