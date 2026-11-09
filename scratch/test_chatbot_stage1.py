import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

from django.test import Client
from app.local_assistant import process_conversational_message

def test_chatbot_stage1():
    print("=== INICIANDO PRUEBAS DE LA ETAPA 1: CHATBOT MEJORADO ===")

    # Test 1: "Hola" -> saludo natural, sin crear presupuesto
    reply1, state1, _ = process_conversational_message("Hola", None)
    assert "¡Hola!" in reply1 or "bienvenida" in reply1.lower()
    assert state1 is None, f"No debería haber borrador creado para 'Hola', pero state={state1}"
    assert "nombre y apellido" not in reply1.lower()
    print("[OK] Caso 1: 'Hola' responde con saludo natural y sin crear presupuesto.")

    # Test 2: "¿Qué podés hacer?" -> explicación amplia de funciones
    reply2, state2, _ = process_conversational_message("¿Qué podés hacer?", None)
    assert "Insumos Médicos" in reply2 or "Presupuestos" in reply2
    assert "Medios de Pago" in reply2
    assert len(reply2) > 200, "La respuesta debe ser amplia y completa"
    assert state2 is None
    print("[OK] Caso 2: '¿Qué podés hacer?' responde con explicación amplia y estructurada.")

    # Test 3: "¿Qué insumos tenemos?" -> información del inventario (10 insumos, stock ilimitado)
    reply3, state3, _ = process_conversational_message("¿Qué insumos tenemos?", None)
    assert "Guantes" in reply3
    assert "ILIMITADO" in reply3
    assert state3 is None
    print("[OK] Caso 3: '¿Qué insumos tenemos?' muestra el inventario oficial sin crear presupuesto.")

    # Test 4: "¿Cuánto cuestan los guantes?" -> precio real, SIN crear presupuesto ni pedir cliente
    reply4, state4, _ = process_conversational_message("¿Cuánto cuestan los guantes?", None)
    assert "2.500" in reply4 or "2500" in reply4
    assert "ILIMITADO" in reply4
    assert state4 is None, f"No debe crear presupuesto para consulta de precio, pero state={state4}"
    assert "nombre y apellido" not in reply4.lower()
    print("[OK] Caso 4: '¿Cuánto cuestan los guantes?' informa el precio real ($2.500) y Stock Ilimitado sin iniciar presupuesto.")

    # Test 5: "Necesito un presupuesto para dos cajas de guantes" -> inicia el flujo de presupuesto
    reply5, state5, _ = process_conversational_message("Necesito un presupuesto para dos cajas de guantes", None)
    assert state5 is not None and state5.get("active") is True
    assert len(state5.get("items", [])) == 1
    assert state5["items"][0]["cantidad"] == 2
    assert state5["items"][0]["subtotal"] == 5000.0
    assert "5000" in reply5 or "5.000" in reply5
    assert state5.get("awaiting_client") is True
    print("[OK] Caso 5: 'Necesito un presupuesto para dos cajas de guantes' inicia el presupuesto ($5.000) bajo demanda.")

    # Test 6: Respondo con un nombre "Dr. Gómez" -> continúa el flujo
    reply6, state6, _ = process_conversational_message("Dr. Gómez", state5)
    assert state6 is not None
    assert state6.get("cliente") == "Dr. Gómez"
    assert state6.get("awaiting_client") is False
    assert "Dr. Gómez" in reply6
    assert "5000" in reply6 or "5.000" in reply6
    assert "¿Confirmás el presupuesto" in reply6 or "confirmar" in reply6.lower()
    print("[OK] Caso 6: Asignación de cliente 'Dr. Gómez' continúa el flujo correctamente.")

    # Test 7: "¿Qué medios de pago acepta UMSA?" con borrador en curso -> respuesta informativa sin alterar borrador
    reply7, state7, _ = process_conversational_message("¿Qué medios de pago acepta UMSA?", state6)
    assert "Efectivo" in reply7
    assert "Tarjeta" in reply7
    assert "Transferencia" in reply7
    assert "Mercado Pago" in reply7
    assert state7 is not None and state7.get("cliente") == "Dr. Gómez"
    assert state7.get("items")[0]["subtotal"] == 5000.0
    print("[OK] Caso 7: '¿Qué medios de pago acepta UMSA?' responde informativamente y preserva el borrador intacto.")

    # Test 8: "Quiero preguntarte otra cosa" -> permite cambiar de tema
    reply8, state8, _ = process_conversational_message("Quiero preguntarte otra cosa", state6)
    assert "por supuesto" in reply8.lower() or "guardado" in reply8.lower()
    assert state8 is not None, "El borrador debe conservarse en segundo plano"
    assert "nombre y apellido" not in reply8.lower()
    print("[OK] Caso 8: 'Quiero preguntarte otra cosa' permite cambiar de tema sin perder el borrador.")

    # Test 9: Retomar el presupuesto previo tras haber cambiado de tema
    reply9, state9, _ = process_conversational_message("Retomemos el presupuesto", state8)
    assert "Dr. Gómez" in reply9
    assert "5000" in reply9 or "5.000" in reply9
    print("[OK] Caso 9: 'Retomemos el presupuesto' recupera el borrador intacto con total y cliente.")

    # Test 10: Confirmación final genera PDF oficial
    reply10, state10, meta10 = process_conversational_message("Confirmo", state9)
    assert state10 is None, "Al confirmar, el borrador se completa"
    assert meta10.get("presupuesto_created") is True
    assert "Presupuesto generado correctamente" in reply10
    print("[OK] Caso 10: Confirmación emite el PDF oficial ReportLab y limpia el estado.")

    print("\nTODAS LAS 10 COMPROBACIONES DE LA ETAPA 1 PASARON CON ÉXITO!")

if __name__ == "__main__":
    test_chatbot_stage1()
