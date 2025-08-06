import os
import logging
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

# Aplicar timezone desde .env si está definida
import os
if os.getenv('TZ'):
    os.environ['TZ'] = os.getenv('TZ')
    import time
    time.tzset()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Obtener valores de las variables de entorno
admin_id_env = os.getenv('TELEGRAM_ADMIN_ID')
if not admin_id_env:
    raise RuntimeError('TELEGRAM_ADMIN_ID must be set')
admin_id = int(admin_id_env)
token = os.getenv('TELEGRAM_BOT_TOKEN')


# Configuración para webhook
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL must be set for webhook mode")
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '8443'))
WEBHOOK_LISTEN = os.getenv('WEBHOOK_LISTEN', '0.0.0.0')
WEBHOOK_SSL_CERT = os.getenv('WEBHOOK_SSL_CERT')
WEBHOOK_SSL_PRIV = os.getenv('WEBHOOK_SSL_PRIV')
if WEBHOOK_URL:
    from urllib.parse import urlparse
    WEBHOOK_PATH = urlparse(WEBHOOK_URL).path
else:
    WEBHOOK_PATH = f'/{token}'

# Parámetros opcionales para telebot.polling (usados solo en modo polling)
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '2'))
POLL_TIMEOUT = int(os.getenv('POLL_TIMEOUT', '10'))
LONG_POLLING_TIMEOUT = int(os.getenv('LONG_POLLING_TIMEOUT', '10'))

# Verificar que el token esté configurado
if not token:
    print("ERROR: No se encontró TELEGRAM_BOT_TOKEN en el archivo .env")
    print("Asegúrate de que el archivo .env existe y contiene tu token")
    exit(1)

logger.info('✅ Configuración cargada correctamente')
