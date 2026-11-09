import os
import sys
import io
import django
import json
from unittest.mock import patch

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, r"c:\Users\valen\OneDrive\Desktop\UMSA-IA-Turnos")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.test import Client
from app.services import STORAGE

def run_hybrid_tests():
    print("=== INICIANDO VALIDACIÓN DEL FLUJO HÍBRIDO DETERMINÍSTICO ===")
    client = Client()

    # 1. Mensaje 1: "Quiero hacer un presupuesto"
    r1 = client.post(
        "/api/chat/",
        data=json.dumps({"message": "Quiero hacer un presupuesto", "module": ""}),
        content_type="application/json"
    )
    assert r1.status_code == 200, f"Error en r1: {r1.content}"
    d1 = r1.json()
    print("1. Usuario: 'Quiero hacer un presupuesto'")
    print("   Respuesta:", d1["answer"])
    assert "nombre y apellido" in d1["answer"]
    assert "error" not in d1.get("answer", "").lower() or "error" not in d1

    # 2. Mensaje 2: "Juan Pérez"
    r2 = client.post(
        "/api/chat/",
        data=json.dumps({"message": "Juan Pérez", "module": ""}),
        content_type="application/json"
    )
    assert r2.status_code == 200, f"Error en r2: {r2.content}"
    d2 = r2.json()
    print("\n2. Usuario: 'Juan Pérez'")
    print("   Respuesta:", d2["answer"])
    assert "Juan Pérez" in d2["answer"]
    assert "productos" in d2["answer"]

    # 3. Mensaje 3: "2 cajas de guantes y 3 cajas de jeringas"
    r3 = client.post(
        "/api/chat/",
        data=json.dumps({"message": "2 cajas de guantes y 3 cajas de jeringas", "module": ""}),
        content_type="application/json"
    )
    assert r3.status_code == 200, f"Error en r3: {r3.content}"
    d3 = r3.json()
    print("\n3. Usuario: '2 cajas de guantes y 3 cajas de jeringas'")
    print("   Respuesta:", d3["answer"])
    assert "GUANTES LATEX DESCARTABLES" in d3["answer"]
    assert "JERINGAS DESCARTABLES" in d3["answer"]
    assert "5000" in d3["answer"]
    assert "10500" in d3["answer"]
    assert "15500" in d3["answer"]
    assert "¿Confirmás el presupuesto?" in d3["answer"]

    # 4. Mensaje 4: "Sí"
    r4 = client.post(
        "/api/chat/",
        data=json.dumps({"message": "Sí", "module": ""}),
        content_type="application/json"
    )
    assert r4.status_code == 200, f"Error en r4: {r4.content}"
    d4 = r4.json()
    print("\n4. Usuario: 'Sí'")
    print("   Respuesta:", d4["answer"])
    assert "Presupuesto generado con éxito" in d4["answer"]
    assert "Juan Pérez" in d4["answer"]
    assert "15500" in d4["answer"]
    assert d4.get("presupuesto_created") is True
    pdf_info = d4.get("presupuesto", {})
    assert os.path.exists(pdf_info["abs_path"]), f"No existe el archivo PDF: {pdf_info['abs_path']}"
    print("   Archivo físico verificado:", pdf_info["abs_path"])

    # Verificar descarga del archivo
    download_url = pdf_info["download_url"]
    r_dl = client.get(download_url)
    assert r_dl.status_code == 200, f"Error descargando PDF: {r_dl.status_code}"
    assert r_dl["Content-Type"] == "application/pdf"
    print("   Descarga verificada vía HTTP 200 application/pdf.")

    # 5. Consulta de inventario: precio
    r_p = client.post(
        "/api/chat/",
        data=json.dumps({"message": "¿Cuánto cuesta una caja de guantes?", "module": ""}),
        content_type="application/json"
    )
    assert r_p.status_code == 200
    dp = r_p.json()
    print("\n5. Consulta: '¿Cuánto cuesta una caja de guantes?'")
    print("   Respuesta:", dp["answer"])
    assert "2500" in dp["answer"]

    # 6. Consulta de inventario: stock
    r_s = client.post(
        "/api/chat/",
        data=json.dumps({"message": "¿Cuánto stock queda de guantes?", "module": ""}),
        content_type="application/json"
    )
    assert r_s.status_code == 200
    ds = r_s.json()
    print("\n6. Consulta: '¿Cuánto stock queda de guantes?'")
    print("   Respuesta:", ds["answer"])
    assert "ILIMITADO" in ds["answer"]

    # 7. Simulación de fallo de créditos de Anthropic en consulta general
    class MockLowCreditsError(Exception):
        pass

    with patch("anthropic.Anthropic.messages") as mock_msg:
        mock_msg.create.side_effect = Exception("Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}}")
        
        r_fail = client.post(
            "/api/chat/",
            data=json.dumps({"message": "Explicame la teoría de la relatividad general", "module": ""}),
            content_type="application/json"
        )
        assert r_fail.status_code == 200
        dfail = r_fail.json()
        print("\n7. Consulta general con simulación de saldo agotado en Anthropic:")
        print("   Respuesta:", dfail["answer"])
        assert "400" not in dfail["answer"]
        assert "invalid_request_error" not in dfail["answer"]
        assert "credit balance is too low" not in dfail["answer"]
        assert "no está disponible" in dfail["answer"]
        print("   -> NO SE MOSTRÓ NINGÚN ERROR TÉCNICO AL USUARIO.")

    print("\n=== TODAS LAS VALIDACIONES HÍBRIDAS COMPLETADAS EXITOSAMENTE ===")

if __name__ == "__main__":
    run_hybrid_tests()
