import os
import sys
import django

sys.path.insert(0, r"c:\Users\valen\OneDrive\Desktop\UMSA-IA-Turnos")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from app.local_assistant import process_local_interaction

print("=== PROBANDO FLUJO COMPLETO DE PRESUPUESTO INTERACTIVO ===")

# Paso 1: "Quiero hacer un presupuesto"
state = None
reply1, state, meta = process_local_interaction("Quiero hacer un presupuesto", state)
print("1. Usuario: 'Quiero hacer un presupuesto'")
print("   Sistema:", reply1)
print("   Estado:", state)
assert state.get("step") == "esperando_nombre"
assert "nombre y apellido" in reply1

# Paso 2: "Juan Pérez"
reply2, state, meta = process_local_interaction("Juan Pérez", state)
print("\n2. Usuario: 'Juan Pérez'")
print("   Sistema:", reply2)
print("   Estado:", state)
assert state.get("step") == "esperando_productos"
assert state.get("cliente") == "Juan Pérez"
assert "Juan Pérez" in reply2

# Paso 3: "2 cajas de guantes y 3 cajas de jeringas"
reply3, state, meta = process_local_interaction("2 cajas de guantes y 3 cajas de jeringas", state)
print("\n3. Usuario: '2 cajas de guantes y 3 cajas de jeringas'")
print("   Sistema:", reply3)
print("   Estado:", state)
assert state.get("step") == "esperando_confirmacion"
assert state.get("total") == 15500
assert "GUANTES LATEX DESCARTABLES" in reply3
assert "JERINGAS DESCARTABLES" in reply3
assert "15500" in reply3
assert "¿Confirmás el presupuesto?" in reply3

# Paso 4: "Sí"
reply4, state, meta = process_local_interaction("Sí", state)
print("\n4. Usuario: 'Sí'")
print("   Sistema:", reply4)
print("   Estado:", state)
print("   Meta:", meta)
assert state is None
assert meta.get("presupuesto_created") is True
assert "UMSA-P-" in reply4
assert "Juan Pérez" in reply4
assert "15500" in reply4

print("\n=== PROBANDO CONSULTAS DE INVENTARIO SIN CLAUDE ===")

# Q1: ¿Cuánto cuesta una caja de guantes?
q1 = "¿Cuánto cuesta una caja de guantes?"
ans1, st1, m1 = process_local_interaction(q1, None)
print("Q:", q1)
print("A:", ans1)
assert "2500" in ans1

# Q2: ¿Cuánto stock queda de guantes?
q2 = "¿Cuánto stock queda de guantes?"
ans2, st2, m2 = process_local_interaction(q2, None)
print("\nQ:", q2)
print("A:", ans2)
assert "ILIMITADO" in ans2

# Q3: ¿Qué materiales tenemos?
q3 = "¿Qué materiales tenemos?"
ans3, st3, m3 = process_local_interaction(q3, None)
print("\nQ:", q3)
print("A:", ans3)
assert "ILIMITADO" in ans3
assert "Guantes látex" in ans3

# Q4: ¿Hay alcohol?
q4 = "¿Hay alcohol?"
ans4, st4, m4 = process_local_interaction(q4, None)
print("\nQ:", q4)
print("A:", ans4)
assert "3000" in ans4
assert "ILIMITADO" in ans4

print("\n=== TODAS LAS PRUEBAS DETERMINÍSTICAS PASARON EXITOSAMENTE ===")
