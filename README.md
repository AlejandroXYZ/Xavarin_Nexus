# Nexus Xavarin 

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.14--slim-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white" alt="Nginx" />
  <img src="https://img.shields.io/badge/Odoo-714B67?style=for-the-badge&logo=odoo&logoColor=white" alt="Odoo" />
</div>

## Descripción General
Nexus Xavarin es un sistema avanzado de automatización de atención al cliente y operaciones, impulsado por Inteligencia Artificial y arquitecturas de alto rendimiento. 
Actúa como un agente inteligente multicanal (Telegram, WhatsApp) capaz de extraer la intención del cliente, consultar el inventario, ofrecer precios y proveer información de la tienda
en tiempo real. En casos difíciles, el sistema pasa el mensaje a una persona para que sea atendido manualmente

Integrado de manera profunda con el ERP Odoo, el sistema une todo para facilitar el control de la empresa y atención a clientes.


## Arquitectura y Tecnologías
Este sistema se diseñó para ser rápido, eficiente y continuo.

*   **Core:** Python 3.14-slim, FastAPI.
*   **Base de Datos & Búsqueda Semántica:** PostgreSQL, manipulando las query SQL con `asyncpg` para máxima velocidad y pgvector para almacenamiento de embeddings.
*   **Inteligencia Artificial:** Groq API aprovechando su velocidad de respuesta.
*   **Validación de Datos:** Pydantic para validir los mensajes de Telegram , WhatsApp y los JSON de respuesta de la IA.
*   **Tareas en Segundo Plano:** ARQ + Redis.
*   **Infraestructura & Orquestación:** Docker, Docker Compose, Nginx, y automatización de despliegue con Bash (`runner.sh`).
*   **Módulos de Odoo Utilizados:** Facturación, Conversaciones, Inventario, Ventas y Automatizaciones.



## Despliegue y Arranque
El script `runner.sh` instala automáticamente los contenedores, PostgreSQL y Odoo.




## Ejecución

```
chmod +x runner.sh
./runner.sh
```



## Endpoints Principales
El sistema recibe datos al instante, los procesa en segundo plano y usa IA para extraer la intención de los mensajes

POST /api/v1/messages/{tenant_db}/{platform}
Endpoint principal para recibir mensajes externos.


Parámetros de Ruta:

tenant_db: Identificador de la base de datos/cliente en el sistema multi-inquilino.

platform: Plataforma de origen (telegram o whatsapp).

Seguridad: El sistema valida la seguridad con claves de API o con firmas nativas según la plataforma.

Procesamiento: Pydantic filtra los datos, Redis los encola y Groq detecta la intención para activar Odoo.


#  Pruebas (Testing)
El código cuenta con  pruebas unitarias y de integración para asegurara que las funciones de procesamiento y extracción con IA sean estables.

Para ejecutar las pruebas:


	pytest -v



### Variables de Entorno
Crea un archivo `.env` en la raíz del proyecto. El sistema requiere aproximadamente 30 variables operativas. Aquí se muestran las más críticas:

```env

# Desarrollo o Produccion
ENTORNO='desarrollo' (para que FastAPI oculte la documentación automática)
API_KEY_HEADERS='string' (X-API-kEY en headers de los endpoints)


# Postgres Environment
POSTGRES_USER='odoo' (SuperUsuario)
POSTGRES_PASSWORD='password'
POSTGRES_DB='postgres' (DB Maestra Inicial)
POSTGRES_HOST_AUTH_METHOD=trust (Eliminar esta linea en producción, permite conexion a los usuarios sin autenticación)

# Odoo Environment (deben ser iguales a las declaradas en postgres)
HOST='db'
USER='odoo'
PASSWORD='password'
DB='odoo_db'
ODOO_URL_BASE='http://odoo:8069' (URL BASE, Cambiar a la real si estás en Producción)
MASTER_PASSWORD='master_password' (Contraseña interna de Odoo para modificar las bases de datos)


# VARIABLES PARA AUTOMATIZACION DE CATALOGO DE ODOO
FASTAPI_WEBHOOK_URL=http://backend:8000/api/v1/catalog/  (ruta endpoint catalogo)
FASTAPI_WEBHOOK_SECRET=MiContraseña57686      (Token de autenticacion)


#USUARIO ADMIN BASE PARA EL CLIENTE ODOO (Odoo Login solamente)
ODOO_USUARIO_ADMIN_BASE='admin'                         (Usuario base para todos los nuevos inquilinos que se registran)
ODOO_PASSWORD_ADMIN_BASE='19456198472' (Contraseña base para todos los inquilinos que se registran, inquilinos deben cambiarla una vez logeados)

# IA 
API_KEY_IA=mi_token (Token API key groq)

# Credenciales de la base de datos Plantilla para todos los inquilinos que se registran
NEW_USER_DB='xavarin' 
NEW_PASSWORD_DB='123Xavarin456'
NEW_DB='nexus_xavarin' (Db donde se guardarán todos los datos de los inquilinos)

# Telegram Credenciales bot de Agencia (Bot encargado de dar alertas y enviar mensajes a los inquilinos por telegram)
TELEGRAM_API=9999 (token Telegram bot)
CHAT_ID_ADMIN='1234567890' (Numero de ID del admin al cual el bot le enviará las alertas del sistema)


# LLAVE DE ENCRIPTACION DE CREDENCIALES 
ENCRYPTION_KEY=334asdfgojowiejf (generar llave con cryptography Fernet)

# Enlaces VPS
URL_API_BASE=http://localhost:8000 (URL del contenedor backend que contiene FASTAPI)

# Usada en WebHook ODOO, funcion actualizar_webhook_url
URL_API_BASE_DOCKER=http://backend:8000 


# Credenciales de BOT IA dentro de plantilla ODoo
BOT_USER_IA='BOT IA'
EMAIL_BOT='bot@bot.com'


# DIRECCION_POSTGRES_ USADA EN EL WORKER , remmplazar {} con datos
DATABASE_URL='postgresql://{usuario}:{password}:5432/{db}'


# WHATSAAP 
# Token de whatsaap business 
META_BEARER_TOKEN="123456"

# Teléfono de Origen del Mensaje para enviarlos
META_PHONE_ID="102938475610293" 


ODOO_BOT_API_KEY=12345 (Generado Automáticamente con runner.sh)

```
