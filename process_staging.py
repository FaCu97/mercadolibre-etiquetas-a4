import os
from pathlib import Path
from db.database import SessionLocal
from services.invoice_service import InvoiceService

workspace = Path(__file__).parent
staging_dir = workspace / 'comprobantes_staging'
pdf_files = [p for p in staging_dir.iterdir() if p.is_file() and p.suffix.lower() == '.pdf']

if not pdf_files:
    print('No PDF files found in staging folder.')
else:
    db = SessionLocal()
    service = InvoiceService(db)
    for pdf_path in pdf_files:
        try:
            print(f'Processing {pdf_path.name} ...')
            service.process_pdf(str(pdf_path))
        except Exception as e:
            print(f'Error processing {pdf_path.name}: {e}')
    db.close()
    print('Finished processing all staging PDFs.')
