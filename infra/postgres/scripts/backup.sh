#!/bin/sh
set -eu
umask 077
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEST=${1:?Uso: backup.sh /ruta/a/backups}
mkdir -p "$DEST"
OUT=$(mktemp -d "$DEST/backup-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")
dc() { docker compose -f "$ROOT/compose.yaml" "$@"; }
for db in gestion conector; do
  dc exec -T postgres pg_dump -U postgres -d "$db" -Fc > "$OUT/$db.dump.partial"
  mv "$OUT/$db.dump.partial" "$OUT/$db.dump"
done
# Roles without password hashes: restore roles using securely retained secrets.
dc exec -T postgres pg_dumpall -U postgres --roles-only --no-role-passwords > "$OUT/roles.sql.partial"
mv "$OUT/roles.sql.partial" "$OUT/roles.sql"
printf '%s\n' 'Backup completo' > "$OUT/COMPLETE"
printf 'Backup listo: %s\n' "$OUT"
