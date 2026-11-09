import os
import sys
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

from django.conf import settings
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from app import services
from app.local_assistant import process_conversational_message

def run_tests():
    print("=== TEST COMPLETO DE INVENTARIO, IMAGENES Y ASISTENTE ===")
    client = Client()

    # 1. Verificar inventario: exactamente 10 insumos
    inv = services.get_inventario()
    print(f"Total productos en inventario: {len(inv)}")
    assert len(inv) == 10, f"Se esperaban 10 productos, hay {len(inv)}"

    nombres_esperados = [
        "Guantes",
        "Jeringas",
        "gasa",
        "algodón",
        "Alcohol",
        "Agua oxigenada",
        "Barbijos descartables",
        "Cinta adhesiva hipoalergénica",
        "Cofias descartables",
        "Camisolines descartables"
    ]

    nombres_actuales = [p["producto"] for p in inv]
    for n in nombres_esperados:
        assert any(n.lower() in act.lower() for act in nombres_actuales), f"Falta el producto requerido: {n}"
    print("[OK] Requisito 1: Los 10 productos requeridos existen en el inventario.")

    # 2. Verificar que cada producto tiene imagen asignada
    for p in inv:
        img = p.get("imagen", "")
        assert img, f"Producto {p['producto']} no tiene imagen"
        assert p.get("stock") == "ILIMITADO", f"Stock de {p['producto']} debe ser ILIMITADO"
        print(f"  - {p['producto']}: ${p['precio_unitario']} | {p['presentacion']} | img: {img}")
    print("[OK] Requisito 2: Cada producto tiene imagen individual y stock ILIMITADO.")

    # 3. Verificar que las URLs de medios responden HTTP 200
    for p in inv:
        img_url = p["imagen"]
        resp = client.get(img_url)
        assert resp.status_code == 200, f"Error al servir {img_url}: status {resp.status_code}"
    # También probar el placeholder
    resp_ph = client.get("/media/productos/placeholder.svg")
    assert resp_ph.status_code == 200, "Error al servir /media/productos/placeholder.svg"
    print("[OK] Requisito 3: Todas las imágenes y el placeholder se sirven correctamente con HTTP 200.")

    # 4. Probar API /api/inventario/save/ (Edición de producto)
    barbijo = next(p for p in inv if "Barbijos" in p["producto"])
    precio_orig = barbijo["precio_unitario"]
    nuevo_precio = 2750

    resp = client.post("/api/inventario/save/", {
        "id": barbijo["id"],
        "producto": barbijo["producto"],
        "presentacion": barbijo["presentacion"],
        "precio_unitario": nuevo_precio,
        "estado": "Disponible"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert data["item"]["precio_unitario"] == nuevo_precio

    # Restaurar precio original
    services.update_or_create_inventario_item({
        "id": barbijo["id"],
        "producto": barbijo["producto"],
        "presentacion": barbijo["presentacion"],
        "precio_unitario": precio_orig,
        "estado": "Disponible"
    })
    print("[OK] Requisito 4: API de edición de productos guarda y persiste cambios.")

    # 5. Probar subida de imagen de prueba desde formulario multipart
    test_img_content = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    test_file = SimpleUploadedFile("custom_test_upload.gif", test_img_content, content_type="image/gif")

    resp_upload = client.post("/api/inventario/save/", {
        "id": barbijo["id"],
        "producto": barbijo["producto"],
        "presentacion": barbijo["presentacion"],
        "precio_unitario": barbijo["precio_unitario"],
        "estado": "Disponible",
        "imagen_file": test_file
    })
    assert resp_upload.status_code == 200
    data_upload = resp_upload.json()
    assert data_upload.get("ok") is True
    assert "item_" in data_upload["item"]["imagen"]
    uploaded_disk_path = settings.MEDIA_ROOT / data_upload["item"]["imagen"].replace("/media/", "")
    assert uploaded_disk_path.exists(), f"El archivo subido no existe en disco: {uploaded_disk_path}"
    print("[OK] Requisito 5: Carga de imagen desde cliente guarda archivo físicamente y actualiza URL.")

    # 6. Probar eliminación de imagen (restaurar a placeholder)
    resp_remove = client.post("/api/inventario/save/", {
        "id": barbijo["id"],
        "producto": barbijo["producto"],
        "presentacion": barbijo["presentacion"],
        "precio_unitario": barbijo["precio_unitario"],
        "estado": "Disponible",
        "quitar_imagen": "1"
    })
    assert resp_remove.status_code == 200
    data_remove = resp_remove.json()
    assert data_remove["item"]["imagen"] == "/media/productos/placeholder.svg"

    # Restaurar imagen original de barbijos
    services.update_or_create_inventario_item({
        "id": barbijo["id"],
        "producto": barbijo["producto"],
        "presentacion": barbijo["presentacion"],
        "precio_unitario": 2500,
        "estado": "Disponible"
    })
    # Asegurar que la imagen queda restaurada a la foto
    inv_now = services.get_inventario()
    barbijo_item = next(p for p in inv_now if "Barbijos" in p["producto"])
    barbijo_item["imagen"] = "/media/productos/7_barbijos_descartables.jpg"
    services.save_inventario(inv_now)
    print("[OK] Requisito 6: Quitar imagen y restaurar imagen oficial funcionan con éxito.")

    # 7. Asistente Conversacional: Consultas de los 4 nuevos productos
    consultas = [
        ("¿Tienen barbijos descartables?", "barbijos"),
        ("¿Cuál es el precio de la cinta adhesiva hipoalergénica?", "cinta"),
        ("¿Tienen cofias descartables y cuánto salen?", "cofias"),
        ("Necesito saber el costo de camisolines descartables", "camisolines")
    ]
    for prompt, palabra_clave in consultas:
        reply, state, _ = process_conversational_message(prompt, None)
        assert palabra_clave in reply.lower() or "$" in reply, f"Respuesta no reconoció el producto en: '{prompt}' -> {reply}"
    print("[OK] Requisito 7: El asistente responde consultas sobre todos los nuevos insumos.")

    # 8. Asistente Conversacional: Creación de Presupuesto con nuevos productos
    turn1, state, _ = process_conversational_message("Quiero hacer un presupuesto para Hospital Central", None)
    turn2, state, _ = process_conversational_message("Agregá 10 barbijos descartables y 5 camisolines descartables", state)
    
    assert state.get("items"), "No se agregaron items al presupuesto"
    assert len(state["items"]) == 2, f"Se esperaban 2 items, se agregaron {len(state['items'])}"
    
    # 10 * 2500 = 25000, 5 * 8000 = 40000 => total 65000
    total = sum(i["subtotal"] for i in state["items"])
    assert total == 65000, f"Total incorrecto: {total} != 65000"
    print(f"[OK] Requisito 8: Presupuesto inteligente calculado correctamente: Total ${total:,.2f}")

    # 9. Confirmación y generación de PDF
    turn3, state, meta = process_conversational_message("Confirmar presupuesto", state)
    assert meta.get("presupuesto_created") is True, "El presupuesto no se marcó como creado"
    assert "presupuesto" in meta, "No se retornó la metadata del presupuesto"
    pdf_info = meta["presupuesto"]
    filename = pdf_info["filename"]
    pdf_path = settings.BASE_DIR / "files_storage" / "presupuestos" / filename
    assert pdf_path.exists(), f"El archivo PDF no existe físicamente en: {pdf_path}"
    resp_pdf = client.get(pdf_info["download_url"])
    assert resp_pdf.status_code == 200, f"Error descargando PDF: {resp_pdf.status_code}"
    assert resp_pdf["Content-Type"] == "application/pdf"
    print(f"[OK] Requisito 9: PDF oficial generado físicamente ({pdf_path.name}) y descargable con HTTP 200.")

    print("\nTODAS LAS COMPROBACIONES DE INVENTARIO Y MEDIOS PASARON CON ÉXITO (9/9)!")

if __name__ == "__main__":
    run_tests()
