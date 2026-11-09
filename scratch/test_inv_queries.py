import re
import unicodedata

def normalize(text):
    text = text.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )

CATALOG = [
    {
        "id": 1,
        "name": "Guantes látex descartables",
        "display": "GUANTES LATEX DESCARTABLES",
        "presentacion": "Caja x 100 U",
        "precio": 2500,
        "keywords": ["guante", "guantes", "latex", "guantes descartables"],
    },
    {
        "id": 2,
        "name": "Jeringas descartables",
        "display": "JERINGAS DESCARTABLES",
        "presentacion": "Caja x 50 U",
        "precio": 3500,
        "keywords": ["jeringa", "jeringas", "jeringas descartables"],
    },
    {
        "id": 3,
        "name": "Rollo de gasa",
        "display": "ROLLO DE GASA",
        "presentacion": "90 cm x 100 m",
        "precio": 1200,
        "keywords": ["rollo de gasa", "rollos de gasa", "gasa", "gasas"],
    },
    {
        "id": 4,
        "name": "Paquete algodón",
        "display": "PAQUETE ALGODÓN",
        "presentacion": "200 g",
        "precio": 1000,
        "keywords": ["paquete algodon", "paquetes algodon", "algodon", "algodones"],
    },
    {
        "id": 5,
        "name": "Alcohol antiséptico",
        "display": "ALCOHOL ANTISÉPTICO",
        "presentacion": "100 ml",
        "precio": 3000,
        "keywords": ["alcohol antiseptico", "alcohol", "alcoholes"],
    },
    {
        "id": 6,
        "name": "Agua oxigenada",
        "display": "AGUA OXIGENADA",
        "presentacion": "100 ml",
        "precio": 3000,
        "keywords": ["agua oxigenada", "oxigenada"],
    },
]

def find_matched_products(text):
    norm = normalize(text)
    matched = []
    # Check agua oxigenada first so it's not confused with other terms
    for prod in sorted(CATALOG, key=lambda p: len(p["name"]), reverse=True):
        for kw in sorted(prod["keywords"], key=len, reverse=True):
            if re.search(r'\b' + re.escape(normalize(kw)) + r'\b', norm):
                matched.append(prod)
                break
    return matched

def handle_inventory_query(text):
    norm = normalize(text)

    # 1. Full inventory list
    if any(phrase in norm for phrase in [
        "que materiales tenemos", "que productos tenemos", "que materiales hay", "que productos hay",
        "cuales son los productos", "materiales disponibles", "productos disponibles", "ver inventario",
        "mostrar inventario", "lista de precios", "listado de precios", "catalogo de productos", "catalogo"
    ]):
        lines = ["📦 **Inventario Oficial de Insumos Médicos (Stock Ilimitado):**\n"]
        for p in CATALOG:
            lines.append(f"• **{p['name']}** — Presentación: {p['presentacion']} — Precio: ${p['precio']} — Stock: **ILIMITADO**")
        lines.append("\nTodos los insumos cuentan con disponibilidad permanente y stock ilimitado.")
        return "\n".join(lines)

    matched = find_matched_products(text)

    # 2. Stock query
    if any(w in norm for w in ["stock", "cuanto queda", "cuantos quedan", "queda", "quedan", "disponibilidad"]):
        if matched:
            res = []
            for p in matched:
                res.append(f"El stock de **{p['display']}** ({p['presentacion']}) es **ILIMITADO**.")
            return "\n".join(res)
        return "El stock de todos los insumos médicos del inventario oficial es **ILIMITADO**."

    # 3. Presentation query
    if any(w in norm for w in ["presentacion", "formato", "tamano", "medida"]):
        if matched:
            res = []
            for p in matched:
                res.append(f"La presentación de **{p['name']}** es **{p['presentacion']}** a un precio de ${p['precio']} (Stock: **ILIMITADO**).")
            return "\n".join(res)

    # 4. Availability query ("Hay alcohol?", "Tienen gasa?")
    if any(norm.startswith(p) or f" {p}" in norm for p in ["hay ", "tienen ", "disponen de ", "existe "]):
        if matched:
            res = []
            for p in matched:
                res.append(f"Sí, disponemos de **{p['name']}** ({p['presentacion']}) a **${p['precio']}** con **STOCK ILIMITADO** permanente.")
            return "\n".join(res)

    # 5. Price query or quantity query ("Cuánto cuesta...", "Cuánto cuestan 2 cajas de guantes y 3 de jeringas?")
    if any(w in norm for w in ["precio", "cuesta", "cuestan", "valor", "cotizacion", "sale", "salen"]):
        if matched:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent))
            from test_parser import parse_items
            items = parse_items(text)
            if items:
                lines = []
                for it in items:
                    lines.append(f"• **{it['display']}**: {it['cantidad']} unidad(es) × ${it['precio_unitario']} = ${it['subtotal']}")
                total = sum(it["subtotal"] for it in items)
                lines.append(f"\n**Total:** ${total} (Stock permanente e ILIMITADO).")
                lines.append("\nPara generar el PDF oficial, podés escribir *'Quiero hacer un presupuesto'*.")
                return "\n".join(lines)
            else:
                res = []
                for p in matched:
                    res.append(f"El precio unitario de **{p['name']}** ({p['presentacion']}) es **${p['precio']}** (Stock: **ILIMITADO**).")
                return "\n".join(res)

    return None

# Test inventory queries
queries = [
    "¿Qué materiales tenemos?",
    "¿Cuánto cuesta una caja de guantes?",
    "¿Cuánto cuestan 2 cajas de guantes?",
    "¿Cuánto cuestan 2 cajas de guantes y 3 cajas de jeringas?",
    "¿Hay alcohol?",
    "¿Qué presentación tiene el algodón?",
    "¿Cuál es el precio de la gasa?",
    "¿Cuánto stock queda de guantes?",
]

for q in queries:
    resp = handle_inventory_query(q)
    print("Q:", q)
    print("A:", resp)
    print("-" * 40)
