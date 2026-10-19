import os
import re
import pdfplumber
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from db.models import Factura

# Solo lectura
engine = create_engine('sqlite:///data/facturas.db')
Session = sessionmaker(bind=engine)
session = Session()

facturas = session.query(Factura).all()
mal_cargadas = []

for f in facturas:
    pdf_path = f.archivo_pdf_path
    if pdf_path.startswith('/app/'):
        pdf_path = pdf_path.replace('/app/', './')
        
    if not os.path.exists(pdf_path):
        base_name = os.path.basename(pdf_path)
        pdf_path = os.path.join('comprobantes', base_name)
        
    if not os.path.exists(pdf_path):
        continue

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            text = page.extract_text() or ""
            
            # Buscar el CUIT distinto al de Cromosol
            cuit_receptor = ""
            cuits = re.findall(r'\b(?:20|23|24|27|30|33)-?\d{8}-?\d\b', text)
            for c in cuits:
                clean = c.replace("-", "")
                if clean != "30500728317":
                    cuit_receptor = clean
                    break
            
            if cuit_receptor == "30719342457":
                mal_cargadas.append((f.numero_comprobante, os.path.abspath(pdf_path)))
                
    except Exception as e:
        pass

for n, p in mal_cargadas:
    print(f"- {n}: {p}")
