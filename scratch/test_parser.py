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
        "unit_words": ["caja", "cajas", "unidad", "unidades", "u", "pares", "par"],
    },
    {
        "id": 2,
        "name": "Jeringas descartables",
        "display": "JERINGAS DESCARTABLES",
        "presentacion": "Caja x 50 U",
        "precio": 3500,
        "keywords": ["jeringa", "jeringas", "jeringas descartables"],
        "unit_words": ["caja", "cajas", "unidad", "unidades", "u"],
    },
    {
        "id": 3,
        "name": "Rollo de gasa",
        "display": "ROLLO DE GASA",
        "presentacion": "90 cm x 100 m",
        "precio": 1200,
        "keywords": ["rollo de gasa", "rollos de gasa", "gasa", "gasas"],
        "unit_words": ["rollo", "rollos", "unidad", "unidades", "u"],
    },
    {
        "id": 4,
        "name": "Paquete algodón",
        "display": "PAQUETE ALGODÓN",
        "presentacion": "200 g",
        "precio": 1000,
        "keywords": ["paquete algodon", "paquetes algodon", "algodon", "algodones"],
        "unit_words": ["paquete", "paquetes", "unidad", "unidades", "u", "bolsa", "bolsas"],
    },
    {
        "id": 5,
        "name": "Alcohol antiséptico",
        "display": "ALCOHOL ANTISÉPTICO",
        "presentacion": "100 ml",
        "precio": 3000,
        "keywords": ["alcohol antiseptico", "alcohol", "alcoholes"],
        "unit_words": ["frasco", "frascos", "botella", "botellas", "unidad", "unidades", "u"],
    },
    {
        "id": 6,
        "name": "Agua oxigenada",
        "display": "AGUA OXIGENADA",
        "presentacion": "100 ml",
        "precio": 3000,
        "keywords": ["agua oxigenada", "oxigenada"],
        "unit_words": ["frasco", "frascos", "botella", "botellas", "unidad", "unidades", "u"],
    },
]

NUMBER_WORDS = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "veinte": 20, "cincuenta": 50, "cien": 100, "ciento": 100, "mil": 1000,
}

def parse_items(text):
    text_norm = normalize(text)
    # Split by separators: ' y ', ',', ';', '\n', ' e '
    # But preserve context
    clauses = re.split(r'[,;\n]|\s+y\s+|\s+e\s+', text_norm)
    found_items = []
    seen_ids = set()

    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue
        
        # Check against each catalog item
        for prod in CATALOG:
            if prod["id"] in seen_ids:
                continue
            matched = False
            # Check keywords (sorted by length descending so "agua oxigenada" beats "agua")
            for kw in sorted(prod["keywords"], key=len, reverse=True):
                kw_norm = normalize(kw)
                if re.search(r'\b' + re.escape(kw_norm) + r'\b', clause):
                    matched = True
                    break
            
            if matched:
                # Extract quantity in this clause
                # Look for digits e.g. "2 cajas", "100", "2"
                qty = None
                # Regex for number near keyword
                num_match = re.search(r'\b(\d+)\b', clause)
                if num_match:
                    qty = int(num_match.group(1))
                else:
                    # Check number words
                    for word, val in NUMBER_WORDS.items():
                        if re.search(r'\b' + word + r'\b', clause):
                            qty = val
                            break
                if qty is None or qty <= 0:
                    qty = 1 # default if mentioned without quantity
                
                subtotal = qty * prod["precio"]
                found_items.append({
                    "id": prod["id"],
                    "producto": prod["name"],
                    "display": prod["display"],
                    "presentacion": prod["presentacion"],
                    "cantidad": qty,
                    "precio_unitario": prod["precio"],
                    "subtotal": subtotal
                })
                seen_ids.add(prod["id"])
    
    # If clauses didn't match (for instance entire text didn't split well), check full text
    if not found_items:
        for prod in CATALOG:
            for kw in sorted(prod["keywords"], key=len, reverse=True):
                kw_norm = normalize(kw)
                m = re.search(r'(?:(\d+|' + '|'.join(NUMBER_WORDS.keys()) + r')\s*(?:[a-záéíóú]+\s+)?)*' + re.escape(kw_norm), text_norm)
                # pattern search around keyword
                kw_pos = text_norm.find(kw_norm)
                if kw_pos != -1 and prod["id"] not in seen_ids:
                    # look before kw for quantity
                    prefix = text_norm[max(0, kw_pos - 25):kw_pos]
                    num_match = re.search(r'(\d+)', prefix)
                    qty = int(num_match.group(1)) if num_match else 1
                    subtotal = qty * prod["precio"]
                    found_items.append({
                        "id": prod["id"],
                        "producto": prod["name"],
                        "display": prod["display"],
                        "presentacion": prod["presentacion"],
                        "cantidad": qty,
                        "precio_unitario": prod["precio"],
                        "subtotal": subtotal
                    })
                    seen_ids.add(prod["id"])
                    break

    return found_items

# Test cases
test_inputs = [
    "2 cajas de guantes y 3 cajas de jeringas",
    "1 rollo de gasa, 4 paquetes de algodón y dos frascos de alcohol",
    "100 cajas de guantes descartables",
    "necesito 10 cajas de jeringas descartables y 5 agua oxigenada",
    "3 guantes y 2 jeringas",
    "500 alcohol",
]

for inp in test_inputs:
    res = parse_items(inp)
    print("IN:", inp)
    for r in res:
        print("  ->", r["display"], r["cantidad"], "x", r["precio_unitario"], "=", r["subtotal"])
    print("  TOTAL:", sum(x["subtotal"] for x in res))
