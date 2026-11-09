import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

from django.test import Client

client = Client()

print("=" * 70)
print("INICIANDO PRUEBAS DE RAZONAMIENTO REAL VÍA ENDPOINT /api/chat/")
print("=" * 70)

def ask(query):
    resp = client.post(
        "/api/chat/",
        data=json.dumps({"message": query, "module": ""}),
        content_type="application/json",
    )
    assert resp.status_code == 200, f"Error {resp.status_code}: {resp.content}"
    data = resp.json()
    assert data["ok"] is True, f"Response not ok: {data}"
    answer = data["answer"]
    return answer

# =========================================================================
# PRUEBAS ESPECÍFICAS DE COMPRENSIÓN (A - H)
# =========================================================================

# Caso A: "Hola, quiero un presupuesto para 4 cajas de guantes"
ansA = ask("Hola, quiero un presupuesto para 4 cajas de guantes")
print("\n[A] 'Hola, quiero un presupuesto para 4 cajas de guantes'")
print("->", ansA)
assert "10000" in ansA or "10.000" in ansA, "Debe incluir el subtotal real de $10.000 (4 x $2.500)"
assert "cliente o profesional" in ansA.lower(), "Debe preguntar por el cliente o profesional faltante"
assert "tenés un borrador de presupuesto guardado para" not in ansA.lower(), "No debe incluir notas de borradores obsoletos"

# Caso B: "Necesito otras dos cajas más"
ansB = ask("Necesito otras dos cajas más")
print("\n[B] 'Necesito otras dos cajas más'")
print("->", ansB)
assert "15000" in ansB or "15.000" in ansB, "Debe acumular 6 cajas dando $15.000"
assert "6 unidades" in ansB.lower() or "6 caja" in ansB.lower(), "Debe indicar 6 unidades o cajas"

# Caso C: "¿Cuánto sale una caja de jeringas?"
ansC = ask("¿Cuánto sale una caja de jeringas?")
print("\n[C] '¿Cuánto sale una caja de jeringas?'")
print("->", ansC)
assert "3500" in ansC, "Debe indicar el precio real de $3.500"
assert "ilimitado" in ansC.lower(), "Debe confirmar stock ilimitado"

# Caso D: "Dejá el presupuesto en pausa. ¿Qué medios de pago aceptan?"
ansD = ask("Dejá el presupuesto en pausa. ¿Qué medios de pago aceptan?")
print("\n[D] 'Dejá el presupuesto en pausa. ¿Qué medios de pago aceptan?'")
print("->", ansD)
assert "efectivo" in ansD.lower() and "mercado pago" in ansD.lower(), "Debe listar medios de pago"
assert "pausado" in ansD.lower(), "Debe confirmar que el presupuesto quedó en pausa"

# Caso E: "Volvamos al presupuesto de antes"
ansE = ask("Volvamos al presupuesto de antes")
print("\n[E] 'Volvamos al presupuesto de antes'")
print("->", ansE)
assert "15000" in ansE or "15.000" in ansE, "Debe retomar el presupuesto de $15.000 acumulado"
assert "6 unidad" in ansE.lower() or "guantes" in ansE.lower(), "Debe contener los insumos guardados"

# Caso F: "Quiero cuatro cajas de guantes" (sin saludo y redacción directa)
# Iniciar sesión limpia para probar caso F de forma independiente
client_clean = Client()
ansF = client_clean.post("/api/chat/", data=json.dumps({"message": "Quiero cuatro cajas de guantes"}), content_type="application/json").json()["answer"]
print("\n[F] 'Quiero cuatro cajas de guantes'")
print("->", ansF)
assert "10000" in ansF or "10.000" in ansF, "Debe calcular 4 cajas = $10.000"
assert "cliente o profesional" in ansF.lower(), "Debe pedir el cliente faltante"

# Caso G: "Quiero saber cuánto cuestan cuatro cajas de guantes, pero todavía no hagas un presupuesto"
ansG = client_clean.post("/api/chat/", data=json.dumps({"message": "Quiero saber cuánto cuestan cuatro cajas de guantes, pero todavía no hagas un presupuesto"}), content_type="application/json").json()["answer"]
print("\n[G] 'Quiero saber cuánto cuestan cuatro cajas de guantes, pero todavía no hagas un presupuesto'")
print("->", ansG)
assert "10000" in ansG or "10.000" in ansG, "Debe calcular $10.000 para las 4 cajas"
assert "sin generar presupuesto" in ansG.lower() or "consulta informativa" in ansG.lower(), "Debe respetar la restricción negativa explícita"

# Caso H: Solicitud de producto inexistente en el inventario
ansH = client_clean.post("/api/chat/", data=json.dumps({"message": "¿Cuánto cuesta un tensiómetro digital?"}), content_type="application/json").json()["answer"]
print("\n[H] '¿Cuánto cuesta un tensiómetro digital?'")
print("->", ansH)
assert "no se encuentra disponible" in ansH.lower() or "no forma parte de nuestro catálogo" in ansH.lower(), "Debe explicar que el producto no está en el catálogo oficial"
assert "guantes" in ansH.lower() and "jeringas" in ansH.lower(), "Debe ofrecer los insumos oficiales disponibles"

print("\n" + "=" * 70)
print("¡TODAS LAS PRUEBAS A - H PASARON CON 100% DE ÉXITO!")
print("=" * 70)
