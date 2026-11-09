import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from app.services import get_inventario
inv = get_inventario()
print(f"Total productos en inventario: {len(inv)}")
for it in inv:
    print(f"ID {it['id']}: {it['producto']} | {it['presentacion']} | ${it['precio_unitario']} | {it.get('imagen')}")
