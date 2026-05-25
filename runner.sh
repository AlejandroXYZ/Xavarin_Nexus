#!/bin/bash
set -e

USUARIO_DB="odoo"
NOMBRE_DB="mi_empresa"

echo "Encendiendo la base de datos"
docker compose up -d db

echo -n "Esperando a que Postgres esté listo..."
while ! docker exec $(docker compose ps -q db) pg_isready -U $USUARIO_DB >/dev/null 2>/dev/null; do
  echo -n "."
  sleep 1
done

echo "Verificando si Odoo ya fue instalado previamente..."

DB_EXISTE=$(docker exec $(docker compose ps -q db) psql -h localhost -U $USUARIO_DB -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$NOMBRE_DB'")

if [ "$DB_EXISTE" == "1" ]; then
  echo "La base de datos existe"
else
  echo "Base de datos nueva. Ejecutando instalación de módulos de Odoo..."
  docker compose run --rm odoo odoo -d "$NOMBRE_DB" -i base,sale,stock,mail,base_automation --stop-after-init
fi
docker compose up -d
