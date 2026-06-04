#!/bin/bash

set -ea
source .env
set +a

echo "Encendiendo contenedores base (DB y Odoo)..."

docker-compose up -d db odoo

echo -n " Esperando a que Postgres esté listo para recibir conexiones..."
while ! docker-compose exec -T db pg_isready -U "$POSTGRES_USER" >/dev/null 2>/dev/null; do
  echo -n "."
  sleep 1
done
echo " Listo!"

echo "Configurando la Contraseña Maestra y Proxy en Odoo..."

[[ "$ENTORNO" == "desarrollo" ]] && estado="False" || estado="True"

docker-compose exec -T odoo python3 -c "
import configparser
config = configparser.ConfigParser()
# Leemos el archivo actual (si está vacío, Python lo maneja sin error)
config.read('/etc/odoo/odoo.conf')

if not config.has_section('options'):
    config.add_section('options')

# Escribimos la contraseña maestra global
config.set('options', 'admin_passwd', '${MASTER_PASSWORD}')

# En producción DEBE ser True. En local puede ser False porque no hay proxy.
config.set('options', 'proxy_mode', '$estado')

with open('/etc/odoo/odoo.conf', 'w') as f:
    config.write(f)
"

docker-compose restart odoo
echo "Contraseña maestra inyectada y Odoo reiniciado."

echo "Verificando si la base de datos plantilla '$DB' ya existe en Postgres..."

DB_EXISTE=$(docker-compose exec -T db env PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB'")
DB_EXISTE=$(echo "$DB_EXISTE" | tr -d '\r\n[:space:]')

if [ "$DB_EXISTE" = "1" ]; then
  echo "La base de datos '$DB' ya existe"
else
  echo "Base de datos nueva detectada. Ejecutando instalación de módulos de Odoo..."
  docker-compose run --rm odoo odoo -d "$DB" -i base,sale,stock,mail,base_automation --load-language=es_VE --stop-after-init

  echo "Cambiando la contraseña del usuario administrador interno..."
  echo "env.ref('base.user_admin').write({'password': '${ODOO_PASSWORD_ADMIN_BASE}'}); env.cr.commit()" | docker-compose run --rm -T odoo odoo shell -d "$DB"

  echo "Creando Usuario Bot y generando API Key"

  BOT_SCRIPT=$(
    cat <<'EOF'
import datetime
import os

# ==========================================
# 1. CREACIÓN DEL BOT Y API KEY
# ==========================================
bot = env['res.users'].search([('login', '=', 'bot@bot.com')], limit=1)

if not bot:
    bot = env['res.users'].create({
        'name': 'BOT IA XAVARIN',
        'login': 'bot@bot.com',
        'email': 'bot@bot.com'
    })
    
    grupos = [env.ref('base.group_user').id, env.ref('base.group_system').id]
    for gid in grupos:
        env.cr.execute("SELECT 1 FROM res_groups_users_rel WHERE uid=%s AND gid=%s", (bot.id, gid))
        if not env.cr.fetchone():
            env.cr.execute("INSERT INTO res_groups_users_rel (uid, gid) VALUES (%s, %s)", (bot.id, gid))

if not env['res.users.apikeys'].search([('user_id', '=', bot.id)]):
    fecha_objeto = datetime.datetime.now() + datetime.timedelta(days=90)
    key = env['res.users.apikeys']._generate('fastapi_integration', bot.id, fecha_objeto)
    print(f"FASTAPI_MAGIC_KEY: {key}")

# ==========================================
# 2. INYECCIÓN DEL WEBHOOK NATIVO DE ODOO
# ==========================================
model_product = env['ir.model'].search([('model', '=', 'product.template')], limit=1)

action = env['ir.actions.server'].search([('name', '=', 'Webhook IA FastAPI')], limit=1)

if not action:
    import os
    
    # 1. Extraemos los IDs de los campos que queremos que Odoo envíe en el JSON
    campos = ['name', 'description', 'list_price', 'qty_available']
    field_ids = env['ir.model.fields'].search([
        ('model', '=', 'product.template'),
        ('name', 'in', campos)
    ]).ids
    
    # 2. Leemos las variables de entorno inyectadas en Docker
    base_url = os.getenv("FASTAPI_WEBHOOK_URL", "http://backend:8000/api/v1/webhook/odoo/product")
    secret = os.getenv("FASTAPI_WEBHOOK_SECRET", "super_secreto")
    
    # 3. Magia Multi-Tenant: Inyectamos el nombre de la DB y el Token directo en la URL
    webhook_url_final = f"{base_url}?tenant={env.cr.dbname}&token={secret}"
    
    # 4. Creamos la Acción usando el estado NATIVO 'webhook' (Cero código inyectado)
    action = env['ir.actions.server'].create({
        'name': 'Webhook IA FastAPI',
        'model_id': model_product.id,
        'state': 'webhook',
        'webhook_url': webhook_url_final,
        'webhook_field_ids': [(6, 0, field_ids)] # Odoo armará el JSON automáticamente con estos campos
    })

    # 5. Creamos el Gatillo
    env['base.automation'].create({
        'name': 'Sincronizar Productos con IA',
        'model_id': model_product.id,
        'trigger': 'on_create_or_write',
        'trigger_field_ids': [(6, 0, field_ids)],
        'action_server_ids': [(4, action.id)]
    })

# Guardamos todos los cambios en la base de datos
env.cr.commit()
EOF
  )
  BOT_OUTPUT=$(echo "$BOT_SCRIPT" | docker-compose run --rm -T odoo odoo shell -d "$DB")
  BOT_KEY=$(echo "$BOT_OUTPUT" | grep "FASTAPI_MAGIC_KEY:" | awk '{print $2}' | tr -d '\r')

  if [ ! -z "$BOT_KEY" ]; then
    sed -i '/^ODOO_BOT_API_KEY=/d' .env

    echo "ODOO_BOT_API_KEY=$BOT_KEY" >>.env
    echo "Bot creado con éxito. API Key inyectada en el archivo .env automáticamente."
  else
    echo "El Bot ya existía o no se requirió generar una nueva llave."
  fi
fi

echo "Levantando el resto de los servicios de la aplicación..."

docker-compose up -d
