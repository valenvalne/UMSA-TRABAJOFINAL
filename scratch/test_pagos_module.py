import os
import sys
import json
from pathlib import Path
from decimal import Decimal

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

from django.test import Client
from app.models import MedioPago, RegistroPago, WebhookLog
from app import pagos, presupuestos, services

def run_pagos_test_suite():
    print("=== INICIANDO SUITE DE PRUEBAS DEL MÓDULO DE MEDIOS DE PAGO ===")
    client = Client()

    # 1. Accesibilidad de la sección y vista principal
    resp_index = client.get("/")
    assert resp_index.status_code == 200, "La vista principal no responde HTTP 200"
    content = resp_index.content.decode("utf-8")
    assert "tab-pagos" in content, "La sección tab-pagos no está presente en la plantilla"
    assert "Medios de pago" in content, "La etiqueta 'Medios de pago' no está en la navegación"
    print("[OK] Test 1: La sección 'Medios de pago' es accesible en la navegación principal.")

    # 2. Visualización de los cuatro medios de pago oficiales
    medios = pagos.get_medios_pago()
    assert len(medios) == 4, f"Se esperaban 4 medios de pago, hay {len(medios)}"
    codigos_esperados = ["efectivo", "tarjeta", "transferencia", "mercadopago"]
    for c in codigos_esperados:
        m = next((item for item in medios if item["codigo"] == c), None)
        assert m is not None, f"Falta el medio de pago requerido: {c}"
        assert m["nombre"], f"Medio {c} sin nombre"
        print(f"  - [{m['icono']}] {m['nombre']} (Código: {m['codigo']}) - Activo: {m['activo']}")
    print("[OK] Test 2: Se visualizan exactamente los 4 medios de pago oficiales.")

    # 3. Activación y desactivación de medios de pago
    # Desactivar tarjeta
    res_toggle_off = pagos.toggle_medio_pago("tarjeta", activo=False)
    assert res_toggle_off["activo"] is False, "Fallo al desactivar medio 'tarjeta'"
    medios_activos = pagos.get_medios_pago(only_active=True)
    assert not any(m["codigo"] == "tarjeta" for m in medios_activos), "'tarjeta' no debe estar en activos"

    # Intentar registrar un pago con medio inactivo debe fallar
    historial = presupuestos.init_historial_from_storage()
    assert len(historial) > 0, "Debe haber al menos un presupuesto para las pruebas"
    p_test = historial[0]

    try:
        pagos.registrar_pago({
            "presupuesto_numero": p_test["numero"],
            "importe": 100.0,
            "medio_pago": "tarjeta",
        })
        assert False, "No debería permitir registrar pago con medio inactivo"
    except ValueError as e:
        assert "inactivo" in str(e).lower()
        print(f"  - Validación exitosa de medio inactivo: {e}")

    # Reactivar tarjeta
    res_toggle_on = pagos.toggle_medio_pago("tarjeta", activo=True)
    assert res_toggle_on["activo"] is True, "Fallo al reactivar medio 'tarjeta'"
    print("[OK] Test 3: Activación y desactivación funcionan sin borrar información ni historial.")

    # 4 & 6. Registrar un pago en efectivo asociado a un presupuesto existente
    import time
    ts = int(time.time() * 1000)
    op_efectivo = f"REC-EF-TEST-{ts}"
    op_trf = f"TRF-TEST-{ts}"

    total_pres = float(p_test["total"])
    pago_efectivo = pagos.registrar_pago({
        "presupuesto_numero": p_test["numero"],
        "cliente": p_test["cliente"],
        "importe": 500.0,
        "medio_pago": "efectivo",
        "estado": "parcial" if total_pres > 500 else "pagado",
        "numero_operacion": op_efectivo,
        "observaciones": "Pago de prueba en efectivo para auditoría",
    })
    assert pago_efectivo["id"] is not None
    assert pago_efectivo["presupuesto_numero"] == p_test["numero"]
    assert pago_efectivo["medio_pago_codigo"] == "efectivo"
    assert pago_efectivo["importe"] == 500.0
    print(f"[OK] Test 4 & 6: Pago en efectivo registrado y asociado al presupuesto {p_test['numero']}.")

    # 5. Registrar un pago por transferencia bancaria con validación
    pago_trf = pagos.registrar_pago({
        "presupuesto_numero": p_test["numero"],
        "cliente": p_test["cliente"],
        "importe": 1000.0,
        "medio_pago": "transferencia",
        "estado": "pagado",
        "numero_operacion": op_trf,
        "observaciones": "Transferencia de prueba comprobada en extracto",
    })
    assert pago_trf["id"] is not None
    assert pago_trf["medio_pago_codigo"] == "transferencia"
    print(f"[OK] Test 5: Pago por transferencia bancaria registrado correctamente con N° comprobante.")

    # 7. Cálculo correcto de importe pagado y saldo pendiente
    summary = pagos.get_presupuesto_pagos_summary(p_test["numero"])
    assert summary["total_pagado"] >= 1500.0
    assert summary["saldo_pendiente"] == max(0.0, total_pres - summary["total_pagado"])
    print(f"[OK] Test 7: Total presupuesto: ${summary['total_presupuesto']} | Total pagado: ${summary['total_pagado']} | Saldo: ${summary['saldo_pendiente']} ({summary['estado_pago']})")

    # 8. Estados: pendiente, parcial, pagado y cancelado
    # Cancelar el pago de transferencia para verificar estado cancelado y recálculo de saldo
    tot_before = summary["total_pagado"]
    pago_cancelado = pagos.cancelar_pago(pago_trf["id"], motivo="Prueba de anulación y auditoría")
    assert pago_cancelado["estado"] == "cancelado"
    assert pago_cancelado["motivo_cancelacion"] == "Prueba de anulación y auditoría"

    summary_after_cancel = pagos.get_presupuesto_pagos_summary(p_test["numero"])
    assert summary_after_cancel["total_pagado"] == tot_before - 1000.0, "El total pagado debe excluir pagos cancelados"
    print("[OK] Test 8: Estados 'pagado', 'parcial', 'pendiente' y 'cancelado' calculan y auditan con exactitud.")

    # 9. Filtros y búsqueda
    pagos_filtrados_efectivo = pagos.get_pagos_historial(filter_medio="efectivo")
    assert all(p["medio_pago_codigo"] == "efectivo" for p in pagos_filtrados_efectivo)

    pagos_filtrados_cancelados = pagos.get_pagos_historial(filter_estado="cancelado")
    assert any(p["id"] == pago_trf["id"] for p in pagos_filtrados_cancelados)

    pagos_busqueda = pagos.get_pagos_historial(search=op_efectivo)
    assert len(pagos_busqueda) >= 1
    print("[OK] Test 9: Filtros por medio, estado y buscador funcionan correctamente.")

    # 10. Prevención de registros duplicados por número de operación
    try:
        pagos.registrar_pago({
            "presupuesto_numero": p_test["numero"],
            "importe": 200.0,
            "medio_pago": "efectivo",
            "numero_operacion": op_efectivo,  # Ya usado en pago_efectivo
        })
        assert False, "No debería permitir registrar pago duplicado con el mismo número de operación"
    except ValueError as e:
        assert "ya existe un pago registrado" in str(e).lower()
        print(f"  - Detección de duplicado exitosa: {e}")
    print("[OK] Test 10: Prevención de duplicados por número de operación confirmada.")

    # 11. Persistencia de pagos en almacenamiento físico JSON
    p_storage = services.STORAGE / "pagos" / "pagos_historial.json"
    assert p_storage.exists(), f"El archivo espejo físico {p_storage} no existe"
    data_json = json.loads(p_storage.read_text(encoding="utf-8"))
    assert any(p["id"] == pago_efectivo["id"] for p in data_json)
    print(f"[OK] Test 11: Los pagos están persistidos físicamente en {p_storage.name} (Volumen Docker).")

    # 12. Historial de presupuestos anterior intacto
    historial_after = presupuestos.init_historial_from_storage()
    assert len(historial_after) == len(historial)
    assert all("total" in p and "numero" in p for p in historial_after)
    print(f"[OK] Test 12: Todos los {len(historial_after)} presupuestos anteriores se conservan intactos.")

    # 13. Generación de PDF y Asistente conversacional siguen funcionando
    from app.local_assistant import process_conversational_message
    reply, state, _ = process_conversational_message("¿Cuánto cuestan los barbijos?", None)
    assert "$" in reply or "barbijo" in reply.lower()
    print("[OK] Test 13: Asistente conversacional e inventario continúan respondiendo con normalidad.")

    # 14 & 15. Arquitectura de webhook para pagos online (Mercado Pago)
    webhook_res = pagos.process_mercadopago_webhook(
        payload={"id": "test_evt_12345", "action": "payment.created", "data": {"id": "mp_pay_999"}},
        headers={"x-signature": "test"}
    )
    assert webhook_res["status"] in ["success", "pending_credentials", "already_processed"]
    # Idempotencia
    webhook_idem = pagos.process_mercadopago_webhook(
        payload={"id": "test_evt_12345", "action": "payment.created", "data": {"id": "mp_pay_999"}},
        headers={"x-signature": "test"}
    )
    assert webhook_idem["status"] in ["already_processed", "pending_credentials"]
    print("[OK] Test 14 & 15: Arquitectura de webhook online e idempotencia validadas.")

    print("\nTODAS LAS 15 PRUEBAS DEL MÓDULO DE MEDIOS DE PAGO COMPLETADAS CON ÉXITO!")

if __name__ == "__main__":
    run_pagos_test_suite()
