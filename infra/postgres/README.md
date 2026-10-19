# PostgreSQL compartido del negocio

Infraestructura independiente para Raspberry Pi 5 (ARM64), 8 GB RAM y SSD.
PostgreSQL 17, dos bases y roles separados: `gestion` / `gestion_app` y
`conector` / `conector_app`. No migra ni modifica la SQLite existente.

## Arranque

Desde la raíz del repositorio, con Python 3 y Docker Compose instalados:

```sh
python3 infra/postgres/scripts/setup.py
docker compose -f infra/postgres/compose.yaml config --quiet
docker compose -f infra/postgres/compose.yaml up -d --build --wait
sh infra/postgres/scripts/verify.sh
```

El setup genera secretos aleatorios con permisos 0600 y nunca los reemplaza.
Los archivos están excluidos de Git; conservarlos en almacenamiento seguro.
Los secrets de Compose son archivos montados, no un almacén cifrado.
Los scripts de inicialización se ejecutan únicamente sobre un volumen vacío.
Cambiar un archivo de contraseña después del primer arranque NO cambia el rol:
rotar mediante `ALTER ROLE` y actualizar también los consumidores.

No hay puerto publicado. El administrador queda reservado a mantenimiento.
La red `negocio-database` es interna; solo incorporar las apps autorizadas.
El contenedor tiene límite de 1,5 GiB, 40 conexiones y shared_buffers de 256 MB.
`effective_cache_size` es una estimación del planificador, no RAM reservada.
Medir con `docker stats` antes de aumentar conexiones o trabajadores.

## Datos en el SSD

El volumen `negocio-infra_postgres_data` persiste al recrear el contenedor.
En la Pi, verificar que el directorio de datos de Docker esté sobre el SSD:

```sh
docker info --format '{{.DockerRootDir}}'
```

Comprobar el filesystem de esa ruta con `findmnt -T /ruta/devuelta`.
No iniciar la instalación definitiva sobre la microSD. No usar `down -v`:
elimina el volumen. En el Mac, el volumen queda dentro de Docker Desktop.
Fijamos la versión mayor 17; una actualización mayor requiere migración.
Para actualizaciones menores: backup, prueba de restauración, reconstruir con `docker compose -f infra/postgres/compose.yaml build --pull` y ejecutar up.

## Conectar otra aplicación

En el Compose de cada app, declarar la red externa:

```yaml
services:
  app:
    networks: [default, database]
networks:
  database:
    external: true
    name: negocio-database
```

Servidor `postgres`, puerto `5432`, base y rol de esa app. Montar únicamente
su archivo de contraseña como secret y leerlo desde la aplicación. Nunca
compartir el secreto administrador. Pool sugerido: 2–4 conexiones por proceso,
sin superar el límite del rol al sumar réplicas. La red default permite a
la app salir a Internet, mientras PostgreSQL solo usa la red interna.

El conector se consume por API, no accediendo desde gestión a sus tablas.
La aplicación actual todavía usa SQLite; su migración exige validar modelos,
transferir datos y reconciliar cantidades antes de cambiar la conexión.

## Backup y restauración

```sh
sh infra/postgres/scripts/backup.sh /ruta/backups
sh infra/postgres/scripts/verify-restore.sh /ruta/backups/backup-FECHA-SUFIJO
```

Se guardan dumps custom de ambas bases y roles sin contraseñas. `COMPLETE`
solo aparece si todos los comandos tuvieron éxito. Las bases se respaldan
por separado; no constituyen una transacción simultánea entre aplicaciones.
La prueba restaura en bases temporales únicas y luego elimina solo esas bases.
No reemplaza bases reales. Probar además funcionalidad de la app en una
restauración de ensayo cuando existan tablas y datos reales.

Para recuperar ante pérdida: preparar una instancia nueva con los mismos
roles y secretos seguros, detener consumidores y restaurar cada dump en su
base vacía con `pg_restore --exit-on-error --no-owner --no-privileges`, usando
el rol de esa app. Al agregar apps, ampliar también backup y verificación.

Ejemplo de cron en la Pi (adaptar rutas y usuario con acceso a Docker):

```cron
0 3 * * * /bin/sh /opt/negocio/infra/postgres/scripts/backup.sh /mnt/backup/negocio >> /var/log/negocio-backup.log 2>&1
```

No se instala el cron automáticamente en el Mac. Elegir un destino externo
a la Pi o replicar allí los backups; un directorio en el mismo SSD es solo
una copia local. Programar también verificaciones y alertas ante fallos.
No hay borrado automático de backups: definir retención según espacio y
necesidad del negocio. Proteger dumps porque contienen información comercial.

## Estado y diagnóstico

```sh
docker compose -f infra/postgres/compose.yaml ps
docker compose -f infra/postgres/compose.yaml logs --tail=100 postgres
```

Healthcheck indica disponibilidad del motor. `verify.sh` comprueba además
credenciales, escritura y aislamiento. No equivale a probar toda la app.
