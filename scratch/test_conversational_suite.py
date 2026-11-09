import os
import sys
import django
import json

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, r"c:\Users\valen\OneDrive\Desktop\UMSA-IA-Turnos")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.test import Client

def test_all_scenarios():
    print("=== TEST SUITE: ASISTENTE CONVERSACIONAL UMSA IA ===")
    client = Client()

    # -------------------------------------------------------------------------
    # PRUEBA A: "Hola"
    # -------------------------------------------------------------------------
    res = client.post("/api/chat/", data=json.dumps({"message": "Hola"}), content_type="application/json")
    assert res.status_code == 200
    data = json.loads(res.content)
    ans = data["answer"]
    assert "Hola" in ans or "ayudarte" in ans
    print(f"[OK] PRUEBA A ('Hola'):\n     Respuesta: {ans[:80]}...")

    # -------------------------------------------------------------------------
    # PRUEBA B: "¿Qué materiales tienen?"
    # -------------------------------------------------------------------------
    res = client.post("/api/chat/", data=json.dumps({"message": "¿Qué materiales tienen?"}), content_type="application/json")
    data = json.loads(res.content)
    ans = data["answer"]
    assert "guantes" in ans.lower()
    assert "jeringas" in ans.lower()
    assert "ILIMITADO" in ans
    print(f"[OK] PRUEBA B ('¿Qué materiales tienen?'):\n     Respuesta incluye insumos y stock ilimitado.")

    # -------------------------------------------------------------------------
    # PRUEBA C: "¿Cuánto sale una caja de guantes?"
    # -------------------------------------------------------------------------
    res = client.post("/api/chat/", data=json.dumps({"message": "¿Cuánto sale una caja de guantes?"}), content_type="application/json")
    data = json.loads(res.content)
    ans = data["answer"]
    assert "2500" in ans or "2.500" in ans
    print(f"[OK] PRUEBA C ('¿Cuánto sale una caja de guantes?'):\n     Respuesta: {ans}")

    # -------------------------------------------------------------------------
    # FLUJO CONVERSACIONAL COMPLETO (PRUEBAS D, E, F, G, H)
    # -------------------------------------------------------------------------
    # Reset session for clean flow
    client_flow = Client()

    # PRUEBA D: "Necesito cotizar materiales para un cliente."
    res = client_flow.post("/api/chat/", data=json.dumps({"message": "Necesito cotizar materiales para un cliente."}), content_type="application/json")
    data = json.loads(res.content)
    ans = data["answer"]
    assert "cliente" in ans.lower() or "nombre" in ans.lower()
    print(f"[OK] PRUEBA D ('Necesito cotizar materiales para un cliente.'):\n     Respuesta: {ans}")

    # PRUEBA E: "Es para María González y necesito 3 cajas de guantes y 2 de jeringas."
    res = client_flow.post("/api/chat/", data=json.dumps({"message": "Es para María González y necesito 3 cajas de guantes y 2 de jeringas."}), content_type="application/json")
    data = json.loads(res.content)
    ans = data["answer"]
    print("DEBUG PRUEBA E ans:", repr(ans))
    assert "María González" in ans
    assert "7500" in ans  # 3 * 2500
    assert "7000" in ans  # 2 * 3500
    assert "14500" in ans # 7500 + 7000
    print(f"[OK] PRUEBA E ('Es para María González y necesito 3 cajas de guantes y 2 de jeringas.'):\n     Detectó cliente y productos. Total: $14500.")

    # PRUEBA F: "Agregá también 4 paquetes de algodón."
    res = client_flow.post("/api/chat/", data=json.dumps({"message": "Agregá también 4 paquetes de algodón."}), content_type="application/json")
    data = json.loads(res.content)
    ans = data["answer"]
    assert "4000" in ans  # 4 * 1000
    assert "18500" in ans # 14500 + 4000
    print(f"[OK] PRUEBA F ('Agregá también 4 paquetes de algodón.'):\n     Acumuló al presupuesto existente. Nuevo Total: $18500.")

    # PRUEBA G: "¿Cuánto queda?"
    res = client_flow.post("/api/chat/", data=json.dumps({"message": "¿Cuánto queda?"}), content_type="application/json")
    data = json.loads(res.content)
    ans = data["answer"]
    assert "18500" in ans
    assert "María González" in ans
    print(f"[OK] PRUEBA G ('¿Cuánto queda?'):\n     Resumen detallado y cálculo confirmado.")

    # PRUEBA H: "Sí, confirmalo y generá el PDF."
    res = client_flow.post("/api/chat/", data=json.dumps({"message": "Sí, confirmalo y generá el PDF."}), content_type="application/json")
    data = json.loads(res.content)
    ans = data["answer"]
    print("DEBUG PRUEBA H ans:", repr(ans))
    print("DEBUG PRUEBA H data:", repr(data))
    assert data["presupuesto_created"] is True

    assert "presupuesto" in data and data["presupuesto"] is not None
    assert "UMSA-P-" in ans or "Presupuesto generado" in ans
    print(f"[OK] PRUEBA H ('Sí, confirmalo y generá el PDF.'):\n     Generó PDF: {data['presupuesto']['filename']} por ${data['presupuesto']['total']}.")

    # -------------------------------------------------------------------------
    # PRUEBA I: Cancelar presupuesto
    # -------------------------------------------------------------------------
    client_cancel = Client()
    # Iniciar presupuesto
    res = client_cancel.post("/api/chat/", data=json.dumps({"message": "Quiero cotizar 5 frascos de alcohol para el Dr. Rossi"}), content_type="application/json")
    data = json.loads(res.content)
    assert "15000" in data["answer"]
    # Cancelar
    res = client_cancel.post("/api/chat/", data=json.dumps({"message": "Cancelá el presupuesto."}), content_type="application/json")
    data = json.loads(res.content)
    ans = data["answer"]
    assert "cancelado" in ans.lower()
    print(f"[OK] PRUEBA I ('Cancelá el presupuesto.'):\n     Respuesta: {ans}")

    # -------------------------------------------------------------------------
    # PRUEBA J: Frase completamente diferente / conversacional libre
    # -------------------------------------------------------------------------
    res = client.post("/api/chat/", data=json.dumps({"message": "El doctor necesita saber si la semana que viene llega un nuevo pedido de insumos"}), content_type="application/json")
    data = json.loads(res.content)
    ans = data["answer"]
    assert len(ans) > 20
    assert "no entiendo" not in ans.lower()
    assert "comando no reconocido" not in ans.lower()
    print(f"[OK] PRUEBA J (Frase libre):\n     Respuesta contextual: {ans[:90]}...")

    # -------------------------------------------------------------------------
    # PRUEBAS EXTRA DE MODIFICACIONES NATURALES
    # -------------------------------------------------------------------------
    client_mod = Client()
    client_mod.post("/api/chat/", data=json.dumps({"message": "Cotizar 2 cajas de guantes y 3 cajas de jeringas para Dr. Gómez"}), content_type="application/json")
    
    # Quitar jeringas
    res = client_mod.post("/api/chat/", data=json.dumps({"message": "Quitá las jeringas"}), content_type="application/json")
    data = json.loads(res.content)
    print("DEBUG EXTRA ans:", repr(data["answer"]))
    assert "5000" in data["answer"] # Solo 2 guantes (2 * 2500)

    print(f"[OK] EXTRA ('Quitá las jeringas'):\n     Eliminó el ítem y recalculó total a $5000.")

    # Cambiar cliente
    res = client_mod.post("/api/chat/", data=json.dumps({"message": "El cliente es otro. Es para Pedro Gómez, no para Juan"}), content_type="application/json")
    data = json.loads(res.content)
    assert "Pedro Gómez" in data["answer"]
    print(f"[OK] EXTRA ('El cliente es otro. Es para Pedro Gómez'):\n     Actualizó cliente a Pedro Gómez.")

    # Modificar cantidad
    res = client_mod.post("/api/chat/", data=json.dumps({"message": "Cambiá los guantes a 4"}), content_type="application/json")
    data = json.loads(res.content)
    assert "10000" in data["answer"] # 4 * 2500 = 10000
    print(f"[OK] EXTRA ('Cambiá los guantes a 4'):\n     Actualizó cantidad y total a $10000.")

    # -------------------------------------------------------------------------
    # PRUEBA MULTI-TURNO PASO A PASO (SECCIÓN 4 DEL PROMPT)
    # -------------------------------------------------------------------------
    client_step = Client()
    # Turno 1: "Quiero hacer un presupuesto."
    r1 = client_step.post("/api/chat/", data=json.dumps({"message": "Quiero hacer un presupuesto."}), content_type="application/json")
    a1 = json.loads(r1.content)["answer"]
    assert "cliente" in a1.lower() or "nombre" in a1.lower()
    print(f"[OK] PASO A PASO T1: {a1}")

    # Turno 2: "Para Juan Pérez."
    r2 = client_step.post("/api/chat/", data=json.dumps({"message": "Para Juan Pérez."}), content_type="application/json")
    a2 = json.loads(r2.content)["answer"]
    assert "Juan Pérez" in a2
    assert "productos" in a2.lower()
    print(f"[OK] PASO A PASO T2: {a2}")

    # Turno 3: "Necesito 3 cajas de guantes."
    r3 = client_step.post("/api/chat/", data=json.dumps({"message": "Necesito 3 cajas de guantes."}), content_type="application/json")
    a3 = json.loads(r3.content)["answer"]
    assert "7500" in a3
    print(f"[OK] PASO A PASO T3: {a3[:80]}...")

    # Turno 4: "Sí, también 2 cajas de jeringas."
    r4 = client_step.post("/api/chat/", data=json.dumps({"message": "Sí, también 2 cajas de jeringas."}), content_type="application/json")
    a4 = json.loads(r4.content)["answer"]
    assert "14500" in a4 # 7500 + 7000
    print(f"[OK] PASO A PASO T4: {a4[:80]}...")

    # Turno 5: "Confirmo"
    r5 = client_step.post("/api/chat/", data=json.dumps({"message": "Confirmo"}), content_type="application/json")
    d5 = json.loads(r5.content)
    assert d5["presupuesto_created"] is True
    print(f"[OK] PASO A PASO T5: Generó PDF por ${d5['presupuesto']['total']}")

    print("\nTODAS LAS PRUEBAS DEL MOTOR CONVERSACIONAL COMPLETADAS CON EXITO (10/10 + EXTRAS + PASO A PASO).")

if __name__ == "__main__":
    test_all_scenarios()
