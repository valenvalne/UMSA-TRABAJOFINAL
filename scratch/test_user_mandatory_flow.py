import os
import sys
import io
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

from django.test import Client

def run_mandatory_10_turns_test():
    print("=== INICIANDO PRUEBAS OBLIGATORIAS DE LAS 10 CONSULTAS ===")
    client = Client()

    # 1. "Hola"
    r1 = client.post("/api/chat/", data=json.dumps({"message": "Hola", "module": ""}), content_type="application/json")
    assert r1.status_code == 200
    a1 = r1.json()["answer"]
    print(f"\n1. 'Hola':\n-> {a1}")
    assert "¡Hola!" in a1 or "bienvenida" in a1.lower()
    assert "nombre y apellido" not in a1.lower()
    assert "agregué los productos" not in a1.lower()

    # 2. "¿Qué podés hacer?"
    r2 = client.post("/api/chat/", data=json.dumps({"message": "¿Qué podés hacer?", "module": ""}), content_type="application/json")
    assert r2.status_code == 200
    a2 = r2.json()["answer"]
    print(f"\n2. '¿Qué podés hacer?':\n-> {a2[:180]}...")
    assert "Insumos Médicos" in a2 or "insumos descartables" in a2.lower()
    assert "Presupuestos" in a2
    assert "Medios de Pago" in a2 or "cobranzas" in a2.lower()
    assert "agregué los productos" not in a2.lower()

    # 3. "¿Cuánto cuestan los guantes de látex?"
    r3 = client.post("/api/chat/", data=json.dumps({"message": "¿Cuánto cuestan los guantes de látex?", "module": ""}), content_type="application/json")
    assert r3.status_code == 200
    a3 = r3.json()["answer"]
    print(f"\n3. '¿Cuánto cuestan los guantes de látex?':\n-> {a3}")
    assert "2500" in a3 or "2.500" in a3
    assert "ILIMITADO" in a3
    assert "nombre y apellido" not in a3.lower()
    assert "agregué los productos" not in a3.lower()

    # 4. "¿Qué productos tienen disponibles?"
    r4 = client.post("/api/chat/", data=json.dumps({"message": "¿Qué productos tienen disponibles?", "module": ""}), content_type="application/json")
    assert r4.status_code == 200
    a4 = r4.json()["answer"]
    print(f"\n4. '¿Qué productos tienen disponibles?':\n-> {a4[:180]}...")
    assert "Guantes" in a4
    assert "Jeringas" in a4
    assert "ILIMITADO" in a4
    assert "agregué los productos" not in a4.lower()

    # 5. "¿Qué medios de pago aceptan?"
    r5 = client.post("/api/chat/", data=json.dumps({"message": "¿Qué medios de pago aceptan?", "module": ""}), content_type="application/json")
    assert r5.status_code == 200
    a5 = r5.json()["answer"]
    print(f"\n5. '¿Qué medios de pago aceptan?':\n-> {a5[:180]}...")
    assert "Efectivo" in a5
    assert "Tarjeta" in a5
    assert "Transferencia" in a5
    assert "Mercado Pago" in a5
    assert "agregué los productos" not in a5.lower()

    # 6. "Necesito preparar un presupuesto para un consultorio"
    r6 = client.post("/api/chat/", data=json.dumps({"message": "Necesito preparar un presupuesto para un consultorio", "module": ""}), content_type="application/json")
    assert r6.status_code == 200
    a6 = r6.json()["answer"]
    print(f"\n6. 'Necesito preparar un presupuesto para un consultorio':\n-> {a6}")
    assert "Consultorio" in a6
    assert "presupuesto" in a6.lower()
    assert "¿Qué insumos" in a6 or "insumos" in a6.lower()

    # 7. "¿Y cuánto cuesta la caja de jeringas?"
    r7 = client.post("/api/chat/", data=json.dumps({"message": "¿Y cuánto cuesta la caja de jeringas?", "module": ""}), content_type="application/json")
    assert r7.status_code == 200
    a7 = r7.json()["answer"]
    print(f"\n7. '¿Y cuánto cuesta la caja de jeringas?':\n-> {a7}")
    assert "3500" in a7 or "3.500" in a7
    assert "Consultorio" in a7 or "presupuesto" in a7.lower()

    # 8. "Dejemos el presupuesto para después. ¿Qué es una gasa?"
    r8 = client.post("/api/chat/", data=json.dumps({"message": "Dejemos el presupuesto para después. ¿Qué es una gasa?", "module": ""}), content_type="application/json")
    assert r8.status_code == 200
    a8 = r8.json()["answer"]
    print(f"\n8. 'Dejemos el presupuesto para después. ¿Qué es una gasa?':\n-> {a8}")
    assert "gasa" in a8.lower()
    assert "algodón" in a8.lower() or "curaciones" in a8.lower() or "heridas" in a8.lower()
    assert "pausado" in a8.lower() or "guardado" in a8.lower() or "después" in a8.lower()

    # 9. "Volvamos al presupuesto anterior"
    r9 = client.post("/api/chat/", data=json.dumps({"message": "Volvamos al presupuesto anterior", "module": ""}), content_type="application/json")
    assert r9.status_code == 200
    a9 = r9.json()["answer"]
    print(f"\n9. 'Volvamos al presupuesto anterior':\n-> {a9}")
    assert "Consultorio" in a9
    assert "Retomamos" in a9 or "presupuesto" in a9.lower()

    # 10. "¿Cuál es la capital de Francia?"
    r10 = client.post("/api/chat/", data=json.dumps({"message": "¿Cuál es la capital de Francia?", "module": ""}), content_type="application/json")
    assert r10.status_code == 200
    a10 = r10.json()["answer"]
    print(f"\n10. '¿Cuál es la capital de Francia?':\n-> {a10}")
    assert "París" in a10 or "Paris" in a10
    assert "agregué los productos" not in a10.lower()
    assert "total: $" not in a10.lower()

    print("\nTODAS LAS 10 CONSULTAS OBLIGATORIAS PASARON CON ÉXITO Y COHERENCIA TOTAL!")

if __name__ == "__main__":
    run_mandatory_10_turns_test()
