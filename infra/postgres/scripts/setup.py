#!/usr/bin/env python3
"""Create local secrets once. Never replace existing credentials."""
from pathlib import Path
import os
import secrets

root = Path(__file__).resolve().parents[1]
folder = root / 'secrets'
folder.mkdir(mode=0o700, exist_ok=True)
for name in ('admin_password', 'gestion_password', 'conector_password'):
    path = folder / name
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if not path.read_text().strip():
            raise SystemExit(f'Archivo vacío: {path}; corregir antes de iniciar.')
        continue
    with os.fdopen(fd, 'w') as output:
        output.write(secrets.token_urlsafe(36) + '\n')
print('Credenciales preparadas, sin mostrar ni reemplazar contraseñas.')
