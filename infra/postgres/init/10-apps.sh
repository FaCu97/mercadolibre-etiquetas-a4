#!/bin/sh
set -eu
# psql reads secrets from environment without interpolating them into shell commands.
export GESTION_PASSWORD="$(cat /run/secrets/gestion_password)"
export CONECTOR_PASSWORD="$(cat /run/secrets/conector_password)"
psql -v ON_ERROR_STOP=1 --username postgres --dbname postgres <<'SQL'
\getenv gestion_password GESTION_PASSWORD
\getenv conector_password CONECTOR_PASSWORD
CREATE ROLE gestion_app LOGIN PASSWORD :'gestion_password' NOSUPERUSER NOCREATEDB NOCREATEROLE CONNECTION LIMIT 12;
CREATE ROLE conector_app LOGIN PASSWORD :'conector_password' NOSUPERUSER NOCREATEDB NOCREATEROLE CONNECTION LIMIT 8;
CREATE DATABASE gestion OWNER gestion_app;
CREATE DATABASE conector OWNER conector_app;
REVOKE ALL ON DATABASE gestion FROM PUBLIC;
REVOKE ALL ON DATABASE conector FROM PUBLIC;
REVOKE ALL ON DATABASE postgres FROM PUBLIC;
REVOKE ALL ON DATABASE template1 FROM PUBLIC;
\connect gestion
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO gestion_app;
\connect conector
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO conector_app;
SQL
unset GESTION_PASSWORD CONECTOR_PASSWORD
