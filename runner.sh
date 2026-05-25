#!/bin/bash
# -e: Detiene el script si un comando falla.
# -a: Exporta automáticamente todas las variables del .env
set -ea
source .env
set +a

echo "🚀 Encendiendo el contenedor de la base de datos (V1)..."
docker-compose up -d db

echo -n "⏳ Esperando a que Postgres esté listo para recibir conexiones..."
# En v1, '-T' es OBLIGATORIO en scripts para desactivar la asignación de TTY interactivo
while ! docker-compose exec -T db pg_isready -U "$POSTGRES_USER" >/dev/null 2>/dev/null; do
  echo -n "."
  sleep 1
done
echo " ¡Listo!"

echo "🔍 Verificando si la base de datos '$DB' ya existe en Postgres..."

# Inyectamos PGPASSWORD y volvemos a usar '-T' para extraer el texto limpiamente
DB_EXISTE=$(docker-compose exec -T db env PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB'")

# Limpiamos posibles saltos de línea ocultos que devuelva Postgres
DB_EXISTE=$(echo "$DB_EXISTE" | tr -d '\r\n[:space:]')

if [ "$DB_EXISTE" = "1" ]; then
  echo "✅ La base de datos '$DB' ya existe. Saltando inicialización."
else
  echo "🆕 Base de datos nueva detectada. Ejecutando instalación de módulos de Odoo..."
  docker-compose run --rm odoo odoo -d "$DB" -i base,sale,stock,mail,base_automation --stop-after-init
fi

echo "🌐 Levantando el resto de los servicios de la aplicación..."
docker-compose up -d
