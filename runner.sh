#!/bin/bash

set -ea
source .env
set +a

echo "Encendiendo contenedores base (DB y Odoo)..."

docker compose up -d db odoo

echo -n " Esperando a que Postgres esté listo para recibir conexiones..."
while ! docker compose exec -T db pg_isready -U "$POSTGRES_USER" >/dev/null 2>/dev/null; do
  echo -n "."
  sleep 1
done
echo " Listo!"

echo "Configurando la Contraseña Maestra y Proxy en Odoo..."

[[ "$ENTORNO" == "desarrollo" ]] && estado="False" || estado="True"

docker compose exec -T odoo python3 -c "
import configparser
config = configparser.ConfigParser(interpolation=None)
# Leemos el archivo actual (si está vacío, Python lo maneja sin error)
config.read('/etc/odoo/odoo.conf')

if not config.has_section('options'):
    config.add_section('options')

# Escribimos la contraseña maestra global
config.set('options', 'admin_passwd', '${MASTER_PASSWORD}')

# En producción DEBE ser True. En local puede ser False porque no hay proxy.
config.set('options', 'proxy_mode', '$estado')

config.set('options', 'list_db', 'False')

config.set('options', 'dbfilter', '^%d$')

with open('/etc/odoo/odoo.conf', 'w') as f:
    config.write(f)
"
docker compose exec -T odoo chown odoo:odoo /etc/odoo/odoo.conf

docker compose restart odoo
echo "Contraseña maestra inyectada y Odoo reiniciado."

echo "Verificando si la base de datos plantilla '$DB' ya existe en Postgres..."

DB_EXISTE=$(docker compose exec -T db env PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB'")
DB_EXISTE=$(echo "$DB_EXISTE" | tr -d '\r\n[:space:]')

if [ "$DB_EXISTE" = "1" ]; then
  echo "La base de datos '$DB' ya existe"
else
  echo "Base de datos nueva detectada. Ejecutando instalación de módulos de Odoo..."
  docker compose run --rm odoo odoo -d "$DB" -i base,sale,stock,mail,base_automation --load-language=es_VE --stop-after-init

  echo "Cambiando la contraseña del usuario administrador interno..."
  echo "env.ref('base.user_admin').write({'password': '${ODOO_PASSWORD_ADMIN_BASE}'}); env.cr.commit()" | docker compose run --rm -T odoo odoo shell -d "$DB"

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

# --- EL FIX DE LOS PERMISOS (MULTIVERSIÓN) ---
xml_ids_permisos = [
    'base.group_user',                 
    'base.group_system',               
    'sales_team.group_sale_manager',   
    'account.group_account_manager'    
]

# Introspección: Averiguamos el nombre correcto del campo según la versión de Odoo
campo_grupos = 'group_ids' if 'group_ids' in bot._fields else 'groups_id'

for xml_id in xml_ids_permisos:
    grupo = env.ref(xml_id, raise_if_not_found=False)
    if grupo:
        # Usamos la variable dinámica que descubrió el nombre correcto
        bot.write({campo_grupos: [(4, grupo.id)]})
# ----------------------------------------------

if not env['res.users.apikeys'].search([('user_id', '=', bot.id)]):
    fecha_objeto = datetime.datetime.now() + datetime.timedelta(days=90)
    key = env['res.users.apikeys']._generate('fastapi_integration', bot.id, fecha_objeto)
    print(f"FASTAPI_MAGIC_KEY: {key}")
# ==========================================
# 2. INYECCIÓN O ACTUALIZACIÓN DEL WEBHOOK NATIVO DE ODOO (PRODUCTOS)
# ==========================================
model_product = env['ir.model'].search([('model', '=', 'product.template')], limit=1)
action = env['ir.actions.server'].search([('name', '=', 'Webhook IA FastAPI')], limit=1)

# Definimos siempre la URL correcta para ESTA base de datos
base_url = os.getenv("URL_API_BASE_DOCKER", "http://backend:8000")
secret = os.getenv("FASTAPI_WEBHOOK_SECRET", "super_secreto")
x_api_key = os.getenv("API_KEY_HEADERS","123344555")
webhook_url_final = f"{base_url}/api/v1/catalog/{env.cr.dbname}?token={secret}"

campos = ['name', 'description', 'list_price', 'qty_available']
field_ids = env['ir.model.fields'].search([
    ('model', '=', 'product.template'),
    ('name', 'in', campos)
]).ids

if action:
    # EL FIX: Si la acción ya existía (heredada de la plantilla), la actualizamos a la fuerza
    action.write({'webhook_url': webhook_url_final})
    print(f"Webhook actualizado a: {webhook_url_final}")
else:
    # Si no existía, la creamos desde cero
    action = env['ir.actions.server'].create({
        'name': 'Webhook IA FastAPI',
        'model_id': model_product.id,
        'state': 'webhook',
        'webhook_url': webhook_url_final,
        'webhook_field_ids': [(6, 0, field_ids)] 
    })

    env['base.automation'].create({
        'name': 'Sincronizar Productos con IA',
        'model_id': model_product.id,
        'trigger': 'on_create_or_write',
        'trigger_field_ids': [(6, 0, field_ids)],
        'action_server_ids': [(4, action.id)]
    })
    print(f"Webhook creado nuevo: {webhook_url_final}")

# ==========================================
# 3. WEBHOOK PARA MENSAJES DE CHAT (NATIVO EN RED INTERNA)
# ==========================================
model_message = env['ir.model'].search([('model', '=', 'mail.message')], limit=1)
action_chat = env['ir.actions.server'].search([('name', '=', 'Webhook Salida Chat FastAPI')], limit=1)

# Usamos el token en la URL, es 100% seguro en la red interna de Docker
base_url = os.getenv("URL_API_BASE_DOCKER", "http://backend:8000")
secret = os.getenv("FASTAPI_WEBHOOK_SECRET", "super_secreto")
webhook_chat_url = f"{base_url}/api/v1/message/{env.cr.dbname}/webhook?token={secret}"

campos_chat = ['body', 'res_id', 'model', 'author_id']
field_chat_ids = env['ir.model.fields'].search([
    ('model', '=', 'mail.message'),
    ('name', 'in', campos_chat)
]).ids

if action_chat:
    action_chat.write({
        'state': 'webhook',
        'webhook_url': webhook_chat_url,
        'webhook_field_ids': [(6, 0, field_chat_ids)],
        'code': False # Limpiamos cualquier código residual
    })
    print(f"Webhook de Chat actualizado a modalidad nativa: {webhook_chat_url}")
else:
    action_chat = env['ir.actions.server'].create({
        'name': 'Webhook Salida Chat FastAPI',
        'model_id': model_message.id,
        'state': 'webhook',
        'webhook_url': webhook_chat_url,
        'webhook_field_ids': [(6, 0, field_chat_ids)] 
    })

    filtro_seguridad = f"[('model', '=', 'discuss.channel'), ('author_id.user_ids', '!=', False), ('author_id', '!=', {bot.id})]"

    env['base.automation'].create({
        'name': 'Sincronizar Respuestas de Chat de Inquilinos',
        'model_id': model_message.id,
        'trigger': 'on_create',
        'filter_domain': filtro_seguridad, 
        'action_server_ids': [(4, action_chat.id)]
    })
    print("Webhook de Chat creado exitosamente en modalidad nativa.")
    env.cr.commit()
EOF
  )
  BOT_OUTPUT=$(echo "$BOT_SCRIPT" | docker compose run --rm -T odoo odoo shell -d "$DB")
  BOT_KEY=$(echo "$BOT_OUTPUT" | grep "FASTAPI_MAGIC_KEY:" | awk '{print $2}' | tr -d '\r')

  if [ ! -z "$BOT_KEY" ]; then
    sed -i '/^ODOO_BOT_API_KEY=/d' .env
    echo "" >>.env
    echo "ODOO_BOT_API_KEY=$BOT_KEY" >>.env
    echo "Bot creado con éxito. API Key inyectada en el archivo .env automáticamente."
  else
    echo "El Bot ya existía o no se requirió generar una nueva llave."
  fi
fi

echo "Levantando el resto de los servicios de la aplicación..."

if [ "$ENTORNO" == "produccion" ]; then
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

elif [ "$ENTORNO" == "desarrollo" ]; then
  docker compose up -d
else
  echo "Variable de Entorno: ENTORNO es igual a $ENTORNO, no válido"
  exit 1
fi
