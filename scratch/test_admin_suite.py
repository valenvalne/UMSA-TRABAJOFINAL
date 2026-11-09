import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.test import RequestFactory
from app.views import (
    dashboard_metrics_api,
    presupuestos_historial_api,
    presupuesto_detail_api,
    search_api,
    chat_api,
    index,
)
from app.presupuestos import get_dashboard_metrics, get_presupuestos_historial
import json

def test_admin_features():
    rf = RequestFactory()
    print("=== INICIANDO VALIDACIÓN DE LAS 5 NUEVAS FUNCIONALIDADES ===")

    # 1. Dashboard con resumen
    print("\n--- 1. DASHBOARD CON RESUMEN ---")
    req = rf.get("/api/dashboard/metrics/")
    resp = dashboard_metrics_api(req)
    data = json.loads(resp.content.decode("utf-8"))
    assert data["ok"] is True
    metrics = data["metrics"]
    print(f"Métricas obtenidas: Hoy={metrics['presupuestos_hoy']}, Pendientes={metrics['presupuestos_pendientes']}, Productos={metrics['productos_disponibles']}, Total={metrics['total_presupuestado_formateado']}")
    assert metrics["productos_disponibles"] == 6
    assert metrics["total_presupuestado"] >= 0
    print("[OK] Dashboard métricas verificado.")

    # 2. Historial de presupuestos
    print("\n--- 2. HISTORIAL DE PRESUPUESTOS ---")
    req = rf.get("/api/presupuestos/historial/")
    resp = presupuestos_historial_api(req)
    data = json.loads(resp.content.decode("utf-8"))
    assert data["ok"] is True
    assert len(data["historial"]) > 0
    primer_presupuesto = data["historial"][0]
    num = primer_presupuesto["numero"]
    print(f"Historial cuenta con {len(data['historial'])} presupuestos. Primer presupuesto: {num} - {primer_presupuesto['cliente']} (${primer_presupuesto['total']})")
    
    # Detalle de presupuesto
    req_det = rf.get(f"/api/presupuestos/detail/?numero={num}")
    resp_det = presupuesto_detail_api(req_det)
    data_det = json.loads(resp_det.content.decode("utf-8"))
    assert data_det["ok"] is True
    assert data_det["presupuesto"]["numero"] == num
    print(f"[OK] Detalle de presupuesto '{num}' obtenido con éxito (Total: ${data_det['presupuesto']['total']}).")

    # 4. Búsqueda global
    print("\n--- 4. BÚSQUEDA GLOBAL ---")
    # Búsqueda por producto
    req_s1 = rf.get("/api/search/?q=jeringas")
    resp_s1 = search_api(req_s1)
    data_s1 = json.loads(resp_s1.content.decode("utf-8"))
    assert data_s1["ok"] is True
    assert len(data_s1["productos"]) > 0
    print(f"[OK] Búsqueda por insumo 'jeringas': {len(data_s1['productos'])} producto(s) encontrado(s).")

    # Búsqueda por presupuesto
    req_s2 = rf.get(f"/api/search/?q={num}")
    resp_s2 = search_api(req_s2)
    data_s2 = json.loads(resp_s2.content.decode("utf-8"))
    assert data_s2["ok"] is True
    assert len(data_s2["presupuestos"]) > 0
    print(f"[OK] Búsqueda por Nº de presupuesto '{num}': {len(data_s2['presupuestos'])} presupuesto(s) encontrado(s).")

    # Búsqueda por lenguaje natural
    req_s3 = rf.get("/api/search/?q=cuanto sale el alcohol")
    resp_s3 = search_api(req_s3)
    data_s3 = json.loads(resp_s3.content.decode("utf-8"))
    assert data_s3["ok"] is True
    print(f"[OK] Búsqueda por lenguaje natural: respuesta generada = '{data_s3['answer'][:60]}...'")

    # 9. Editar presupuesto antes de generar (Multi-turn conversacional determinista)
    print("\n--- 9. EDITAR PRESUPUESTO ANTES DE GENERAR ---")
    from app.local_assistant import process_conversational_message

    # Turno 1: Inicio de presupuesto
    ans1, d1, meta1 = process_conversational_message("Presupuesto para Dr. Gomez: 2 cajas de jeringas y 3 de alcohol", None)
    print("Turno 1: Solicitud inicial")
    assert not meta1.get("presupuesto_created")
    assert d1 is not None and "items" in d1
    # 2 jeringas ($3500 c/u = $7000), 3 alcohol ($3000 c/u = $9000) -> subtotal $16000
    sub1 = sum(it["subtotal"] for it in d1["items"])
    assert sub1 == 16000
    print(f" -> Subtotal: ${sub1} (Sin generar PDF)")

    # Turno 2: Modificación - "En vez de 2 jeringas quiero 5"
    ans2, d2, meta2 = process_conversational_message("En vez de 2 jeringas quiero 5", d1)
    assert not meta2.get("presupuesto_created")
    # 5 jeringas ($3500 c/u = $17500), 3 alcohol ($3000 c/u = $9000) -> subtotal $26500
    sub2 = sum(it["subtotal"] for it in d2["items"])
    assert sub2 == 26500
    print(f" -> Modificación a 5 jeringas: Subtotal ${sub2}")

    # Turno 3: Consulta hipotética - "¿Cuánto queda si saco el alcohol?"
    ans3, d3, meta3 = process_conversational_message("¿Cuánto queda si saco el alcohol?", d2)
    assert not meta3.get("presupuesto_created")
    # Debe responder hipotéticamente sin modificar el borrador
    print(f" -> Consulta hipotética: '{ans3[:70]}...'")
    assert "quedaría" in ans3.lower() or "quedaria" in ans3.lower() or "$" in ans3

    # Turno 4: Agregar insumos adicionales - "Agregá 2 cajas de guantes"
    ans4, d4, meta4 = process_conversational_message("Agregá 2 cajas de guantes", d3)
    assert not meta4.get("presupuesto_created")
    # +2 guantes ($2500 c/u = $5000) -> subtotal $31500
    sub4 = sum(it["subtotal"] for it in d4["items"])
    assert sub4 == 31500
    print(f" -> Suma de 2 guantes: Subtotal ${sub4}")

    # Turno 5: "Agregá 3 más" (a los guantes)
    ans5, d5, meta5 = process_conversational_message("Agregá 3 más", d4)
    assert not meta5.get("presupuesto_created")
    # 2 + 3 = 5 guantes (+ $7500) -> subtotal $39000
    sub5 = sum(it["subtotal"] for it in d5["items"])
    assert sub5 == 39000
    print(f" -> 'Agregá 3 más': Subtotal ${sub5}")

    # Turno 6: Quitar insumo - "Quitá las jeringas"
    ans6, d6, meta6 = process_conversational_message("Quitá las jeringas", d5)
    assert not meta6.get("presupuesto_created")
    # 5 guantes ($12500) + 3 alcohol ($9000) = $21500
    sub6 = sum(it["subtotal"] for it in d6["items"])
    assert sub6 == 21500
    print(f" -> 'Quitá las jeringas': Subtotal ${sub6}")

    # Turno 7: Confirmación explícita - "Confirmo"
    ans7, d7, meta7 = process_conversational_message("Confirmo", d6)
    assert meta7.get("presupuesto_created") is True
    print(f" -> Confirmación oficial: PDF emitido correctamente ({meta7['presupuesto']['numero']}).")

    # 10. IA integrada al panel (Verificación de vista principal y contexto)
    print("\n--- 10. IA INTEGRADA AL PANEL ---")
    req_index = rf.get("/")
    resp_index = index(req_index)
    assert resp_index.status_code == 200
    html = resp_index.content.decode("utf-8")
    assert "Asistente UMSA" in html
    assert "¿En qué puedo ayudarte?" in html
    assert "chatDraftBanner" in html
    print("[OK] Interfaz de IA integrada y banner de borrador presentes en el template.")

    print("\n=======================================================")
    print("TODAS LAS 5 NUEVAS FUNCIONALIDADES OPERATIVAS Y APROBADAS")
    print("=======================================================")

if __name__ == "__main__":
    test_admin_features()
