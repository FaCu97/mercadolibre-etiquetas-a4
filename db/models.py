from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)  # Nombre visual de referencia
    cuit = Column(String, unique=True, index=True, nullable=True)  # Clave unívoca de emparejamiento
    nombre_cianbox = Column(String, nullable=True)  # Nombre EXACTO registrado en Cianbox (para Selenium)
    id_cianbox = Column(String, nullable=True)  # ID interno de Cianbox (ej: "8")
    razon_social = Column(String, nullable=True)  # Razón Social legal oficial
    parser_type = Column(String, default="default")  # ej: "cromosol", "genai", "default"
    created_at = Column(DateTime, default=datetime.utcnow)

    facturas = relationship("Factura", back_populates="proveedor")


class Factura(Base):
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    
    numero_comprobante = Column(String, index=True, nullable=False)
    tipo_comprobante = Column(String, nullable=False)  # "Factura A", "Nota de Credito A", etc.
    fecha_emision = Column(String, nullable=True)
    
    neto = Column(Float, default=0.0)
    iva = Column(Float, default=0.0)
    percepciones = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    
    archivo_pdf_path = Column(String, nullable=False)
    archivo_nombre = Column(String, nullable=False)
    mueve_stock = Column(Boolean, default=True)
    cuit_receptor = Column(String, nullable=True)

    
    # Estados posibles: PENDIENTE_CARGA, CARGADA_CIANBOX, ERROR_PROCESAMIENTO, ERROR_CARGA
    estado = Column(String, default="PENDIENTE_CARGA", index=True)
    motivo_error = Column(Text, nullable=True)
    
    fecha_ingreso = Column(DateTime, default=datetime.utcnow)
    fecha_procesamiento = Column(DateTime, nullable=True)

    proveedor = relationship("Proveedor", back_populates="facturas")
    items = relationship("FacturaItem", back_populates="factura", cascade="all, delete-orphan")
    logs = relationship("ProcesoLog", back_populates="factura", cascade="all, delete-orphan")

class FacturaItem(Base):
    __tablename__ = "factura_items"

    id = Column(Integer, primary_key=True, index=True)
    factura_id = Column(Integer, ForeignKey("facturas.id"), nullable=False)
    
    codigo = Column(String, nullable=True)
    descripcion = Column(String, nullable=False)
    cantidad = Column(Float, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    factura = relationship("Factura", back_populates="items")

class ProcesoLog(Base):
    __tablename__ = "proceso_logs"

    id = Column(Integer, primary_key=True, index=True)
    factura_id = Column(Integer, ForeignKey("facturas.id"), nullable=True)
    
    nivel = Column(String, default="INFO")  # INFO, WARNING, ERROR
    mensaje = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    factura = relationship("Factura", back_populates="logs")

# ==============================================================================
# NUEVOS MODELOS: CONFIGURACIÓN DINÁMICA EN SQLITE
# ==============================================================================

class CasillaEmail(Base):
    __tablename__ = "casillas_email"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)  # ej: "Casilla Principal Compras"
    server = Column(String, nullable=False, default="imap.gmail.com")
    user = Column(String, nullable=False)
    password = Column(String, nullable=False)
    folder = Column(String, nullable=False, default="INBOX")
    activa = Column(Boolean, default=True)

class ConfiguracionSistema(Base):
    __tablename__ = "configuracion_sistema"

    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String, unique=True, index=True, nullable=False)
    valor = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
