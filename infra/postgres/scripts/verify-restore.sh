#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKUP=${1:?Uso: verify-restore.sh /ruta/backup-completo}
[ -f "$BACKUP/COMPLETE" ] || { echo 'Backup incompleto'; exit 1; }
dc() { docker compose -f "$ROOT/compose.yaml" "$@"; }
# Only drop a unique temporary database created successfully by this invocation.
TARGET="restore_check_$(date +%s)_$$"
created=false
cleanup() {
  if [ "$created" = true ]; then
    dc exec -T postgres dropdb -U postgres "$TARGET"
  fi
}
trap cleanup EXIT
trap 'exit 1' INT TERM
for app in gestion conector; do
  dc exec -T postgres createdb -U postgres -T template0 "$TARGET"
  created=true
  dc exec -T postgres pg_restore -U postgres --exit-on-error --no-owner --no-privileges -d "$TARGET" < "$BACKUP/$app.dump"
  dc exec -T postgres psql -U postgres -d "$TARGET" -v ON_ERROR_STOP=1 -c 'SELECT count(*) AS restored_tables FROM pg_tables WHERE schemaname = '\''public'\'';'
  dc exec -T postgres dropdb -U postgres "$TARGET"
  created=false
done
printf '%s\n' 'OK: ambos dumps restaurados en bases temporales.'
