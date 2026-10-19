#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
dc() { docker compose -f "$ROOT/compose.yaml" "$@"; }
# TCP checks ensure passwords and database permissions really apply.
for app in gestion conector; do
  dc exec -T postgres sh -eu -c '
    export PGPASSWORD="$(cat /run/secrets/${1}_password)"
    psql -h 127.0.0.1 -U "${1}_app" -d "$1" -v ON_ERROR_STOP=1 -c "BEGIN; CREATE TABLE public.connector_probe (id integer); INSERT INTO public.connector_probe VALUES (1); SELECT * FROM public.connector_probe; ROLLBACK;" >/dev/null
    if [ "$1" = gestion ]; then other=conector; else other=gestion; fi
    if psql -h 127.0.0.1 -U "${1}_app" -d "$other" -c "SELECT 1" >/dev/null 2>&1; then
      echo "ERROR: acceso cruzado permitido"; exit 1
    fi
    export PGPASSWORD=deliberately-invalid-test-password
    if psql -h 127.0.0.1 -U "${1}_app" -d "$1" -c "SELECT 1" >/dev/null 2>&1; then
      echo "ERROR: contraseña inválida aceptada"; exit 1
    fi
  ' sh "$app"
done
printf '%s\n' 'OK: escritura transaccional, aislamiento y rechazo de contraseña inválida.'
