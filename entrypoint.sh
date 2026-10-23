#!/bin/sh
set -e

# Esperar a que la base de datos esté lista
echo "Esperando que la base de datos esté disponible..."
python << 'EOF'
import os, sys, time, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connections
from django.db.utils import OperationalError

for i in range(30):
    try:
        connection = connections['default']
        connection.cursor()
        print("Base de datos conectada correctamente.")
        sys.exit(0)
    except OperationalError:
        time.sleep(1)

print("No se pudo conectar a la base de datos tras 30 segundos.")
sys.exit(1)
EOF

# Ejecutar migraciones automáticas
echo "Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

# Recopilar archivos estáticos si no están presentes (por ejemplo, al montar volúmenes en local)
if [ ! -d "/app/staticfiles" ] || [ -z "$(ls -A /app/staticfiles 2>/dev/null)" ]; then
    echo "Recopilando archivos estáticos..."
    python manage.py collectstatic --noinput
fi

# Iniciar el proceso principal
echo "Iniciando servidor..."
exec "$@"
