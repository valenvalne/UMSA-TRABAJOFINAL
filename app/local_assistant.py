import re
import unicodedata
import logging
from .services import (
    get_inventario,
    append_memory,
    load_history,
    save_history,
    list_files_detailed,
    get_memory_content,
)
from .presupuestos import generate_presupuesto_pdf

logger = logging.getLogger(__name__)

# Mapeo de palabras numéricas en español
NUMBER_WORDS = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "quince": 15, "veinte": 20, "veinticinco": 25,
    "treinta": 30, "cincuenta": 50, "cien": 100, "ciento": 100,
    "doscientos": 200, "quinientos": 500, "mil": 1000,
}

# 10 Insumos Médicos Oficiales de UMSA
PRODUCT_KEYWORDS = {
    1: ["guantes latex descartables", "guantes descartables", "guantes de latex", "guantes latex", "guantes", "guante", "latex"],
    2: ["jeringas descartables", "jeringa descartable", "jeringas", "jeringa"],
    3: ["rollo de gasa", "rollos de gasa", "gasa", "gasas"],
    4: ["paquete algodon", "paquetes algodon", "paquete de algodon", "paquetes de algodon", "algodon", "algodones"],
    5: ["alcohol antiseptico", "alcohol medicinal", "alcohol"],
    6: ["agua oxigenada", "oxigenada"],
    7: ["barbijos descartables", "barbijo descartable", "barbijos", "barbijo", "mascarilla", "mascarillas", "tapaboca", "tapabocas"],
    8: ["cinta adhesiva hipoalergenica", "cinta adhesiva", "cinta hipoalergenica", "cinta micropore", "cinta de papel", "cinta"],
    9: ["cofias descartables", "cofia descartable", "cofias", "cofia", "gorro quirurgico", "gorros descartables"],
    10: ["camisolines descartables", "camisolin descartable", "camisolines", "camisolin", "bata quirurgica", "batas descartables"],
}

PRODUCT_DISPLAY_NAMES = {
    1: "Guantes látex descartables (GUANTES LATEX DESCARTABLES - Caja x 100 U)",
    2: "Jeringas descartables (JERINGAS DESCARTABLES - Caja x 50 U)",
    3: "Rollo de gasa (ROLLO DE GASA - 90 cm x 100 m)",
    4: "Paquete algodón (PAQUETE ALGODON - 200 g)",
    5: "Alcohol antiséptico (ALCOHOL ANTISEPTICO - 100 ml)",
    6: "Agua oxigenada (AGUA OXIGENADA - 100 ml)",
    7: "Barbijos descartables (BARBIJOS DESCARTABLES - Caja x 50 U)",
    8: "Cinta adhesiva hipoalergénica (CINTA ADHESIVA - Rollo x 1 U)",
    9: "Cofias descartables (COFIAS DESCARTABLES - Paquete x 100 U)",
    10: "Camisolines descartables (CAMISOLINES DESCARTABLES - Paquete x 10 U)",
}

PRODUCT_SHORT_NAMES = {
    1: "guantes",
    2: "jeringas",
    3: "gasa",
    4: "algodón",
    5: "alcohol",
    6: "agua oxigenada",
    7: "barbijos",
    8: "cinta adhesiva",
    9: "cofias",
    10: "camisolines",
}


def normalize_text(text: str) -> str:
    """Normaliza texto quitando acentos y pasando a minúsculas."""
    if not text:
        return ""
    text = text.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def clean_text_words(text: str) -> str:
    """Normaliza y reemplaza signos de puntuación por espacios."""
    norm = normalize_text(text)
    return re.sub(r"[^\w\s]", " ", norm)


def clean_client_name(name: str) -> str:
    """Limpia el nombre de un cliente quitando palabras parásitas o puntuación."""
    if not name:
        return ""
    cleaned = re.sub(r"^[,\.\s\:\-]+|[,\.\s\:\-]+$", "", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    parts = cleaned.split(" ")
    # Quitar artículos al inicio si acompaña un sustantivo institucional
    if parts and parts[0].lower() in ["un", "una", "el", "la"] and len(parts) > 1:
        parts = parts[1:]
    titled = []
    for p in parts:
        if p.lower() in ["dr.", "dra.", "lic.", "ing.", "prof.", "sr.", "sra."]:
            titled.append(p.capitalize())
        elif p.lower() in ["de", "del", "la", "las", "los", "y"]:
            titled.append(p.lower())
        else:
            titled.append(p.capitalize())
    return " ".join(titled)


def extract_client_name(text: str) -> str | None:
    """
    Extrae el nombre del cliente de frases explícitas como:
    - 'Es para María González y necesito...'
    - 'Para el Dr. Roberto Gómez'
    - 'A nombre de Juan Pérez'
    - 'Cliente: Clínica del Sol'
    - 'Necesito preparar un presupuesto para un consultorio'
    """
    patterns = [
        r"(?:es\s+para|cambia(?:r)?\s+(?:el\s+cliente\s+)?a|a\s+nombre\s+de)\s+((?:(?:dr|dra|lic|ing|prof|sr|sra)\.?\s+)?[^,;\.\n:]+)",
        r"(?:cliente(?:\s+es|\s*:)?)\s+((?:(?:dr|dra|lic|ing|prof|sr|sra)\.?\s+)?[^,;\.\n:]+)",
        r"\bpara\s+((?:(?:dr|dra|lic|ing|prof|sr|sra)\.?\s+)?[^,;\.\n:]+)",
    ]

    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw_target = m.group(1).strip()
            split_delims = re.split(
                r"[:]\s*|\s+no\s+para|\s+en\s+lugar|\s+y\s+necesito|\s+y\s+quiero|\s+y\s+|\s+e\s+|\s+con\s+|\s+por\s+|\s+de\s+\d+|\s+\d+",
                raw_target,
                flags=re.IGNORECASE
            )
            cand = split_delims[0].strip().rstrip(":")
            cand_norm = normalize_text(cand)
            invalid = [
                "un cliente", "el cliente", "un medico", "una clinica", "cotizar",
                "presupuesto", "presupuestar", "hacer", "saber", "comprar", "mi",
                "ver", "insumo", "insumos", "material", "materiales", "esto", "todo",
                "otro tema", "otra cosa", "saber el precio", "los guantes", "despues",
                "mas tarde", "otro dia"
            ]
            product_or_qty_tokens = [
                "caja", "cajas", "paquete", "paquetes", "rollo", "rollos", "unidad", "unidades",
                "guante", "guantes", "jeringa", "jeringas", "gasa", "gasas", "algodon",
                "alcohol", "oxigenada", "barbijo", "barbijos", "cinta", "cofia", "cofias",
                "camisolin", "camisolines"
            ]
            if any(p_tok in cand_norm for p_tok in product_or_qty_tokens):
                continue
            cand_tokens = cand_norm.split()
            # Si empieza con dígitos o palabras numéricas (distintas de artículos 'un'/'una')
            if cand_tokens and (cand_tokens[0].isdigit() or (cand_tokens[0] in NUMBER_WORDS and cand_tokens[0] not in ["un", "una"])):
                continue
            if len(cand) >= 3 and not any(cand_norm == inv or cand_norm.startswith(inv + " ") for inv in invalid):
                return clean_client_name(cand)

    return None


def is_valid_person_or_client_name(text: str) -> tuple[bool, str]:
    """
    Determina si una respuesta del usuario corresponde genuinamente al nombre
    de un cliente, profesional o institución médica cuando se está solicitando ese dato.
    Evita rotundamente confundir preguntas, órdenes, saludos, insumos o frases numéricas con nombres.
    """
    if not text:
        return False, ""
    raw = text.strip()
    norm = normalize_text(raw)

    if "?" in raw or "¿" in raw:
        return False, ""

    forbidden_exact = {
        "hola", "buenas", "buen dia", "buenos dias", "buenas tardes", "buenas noches",
        "gracias", "muchas gracias", "chau", "adios", "si", "no", "ok", "dale", "de acuerdo",
        "confirmo", "cancelar", "cancela", "anular", "otra cosa", "otro tema", "ayuda",
        "que podes hacer", "medios de pago", "transferencia", "mercado pago", "efectivo",
        "cuanto cuesta", "cuanto sale", "presupuesto", "no se", "dejame pensar", "espera"
    }
    if norm in forbidden_exact:
        return False, ""

    forbidden_tokens = {
        "que", "cual", "cuales", "como", "cuanto", "cuantos", "cuanta", "cuantas",
        "cuando", "donde", "por", "porque", "para", "medios", "medio", "pago", "pagos",
        "tarjeta", "transferencia", "mercadopago", "efectivo", "banco", "cbu", "alias",
        "presupuesto", "presupuestos", "cotizacion", "cotizaciones", "precio", "precios",
        "costo", "costos", "inventario", "insumo", "insumos", "producto", "productos",
        "stock", "panel", "sistema", "archivo", "archivos", "modulo", "modulos",
        "otra", "otro", "otras", "otros", "cosa", "tema", "cambiar", "preguntar", "consulta", "duda",
        "cancelar", "anular", "espera", "dejame", "pensar", "despues", "luego",
        "tienen", "tenes", "hay", "venden", "aceptan", "podes", "puedo",
        "necesito", "quiero", "mas", "menos", "agrega", "suma", "pone", "ponele",
        "caja", "cajas", "paquete", "paquetes", "rollo", "rollos", "unidad", "unidades",
        "frasco", "frascos", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "cien", "mil"
    }

    words = raw.split()
    if not words or len(words) > 6:
        return False, ""

    honorifics = ["dr.", "dra.", "dr", "dra", "lic.", "lic", "ing.", "ing", "prof.", "prof", "sr.", "sr", "sra.", "sra"]
    first_w = normalize_text(words[0]).replace(".", "")
    if first_w in honorifics and len(words) >= 2:
        return True, clean_client_name(raw)

    extracted = extract_client_name(raw)
    if extracted:
        return True, extracted

    if 1 <= len(words) <= 5:
        norm_words = [normalize_text(w) for w in words]
        if any(w in forbidden_tokens for w in norm_words):
            return False, ""
        if any(w.isdigit() for w in norm_words):
            return False, ""
        if len(words) == 1 and norm in ["consultorio", "clinica", "sanatorio", "hospital"]:
            return True, clean_client_name(raw)
        if len(words) >= 2 and re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\.\s]+$", raw):
            return True, clean_client_name(raw)

    return False, ""


def detect_product_id(text: str) -> int | None:
    """Devuelve el ID del insumo médico mencionado en el texto si existe."""
    norm = normalize_text(text)
    for prod_id, kws in PRODUCT_KEYWORDS.items():
        for kw in sorted(kws, key=len, reverse=True):
            if re.search(r"\b" + re.escape(normalize_text(kw)) + r"\b", norm):
                return prod_id
    return None


def extract_quantity_near_keyword(clause: str, kw_pos: int) -> int:
    """
    Extrae la cantidad numérica asociada al insumo médico.
    Examina los tokens hacia la izquierda del producto, saltando unidades
    como 'cajas de', 'paquetes de', 'unidades de', etc., evitando tomar
    artículos de otras palabras como 'un presupuesto'.
    """
    prefix = clause[max(0, kw_pos - 40):kw_pos]
    tokens = re.findall(r"\b\w+\b", prefix)
    tokens.reverse()
    unit_fillers = {"caja", "cajas", "paquete", "paquetes", "rollo", "rollos", "unidad", "unidades", "frasco", "frascos", "de", "del", "por"}

    for tok in tokens:
        if tok in unit_fillers:
            continue
        if tok.isdigit():
            val = int(tok)
            if val > 0:
                return val
        if tok in NUMBER_WORDS:
            return NUMBER_WORDS[tok]
        if tok in {"para", "presupuesto", "cotizacion", "necesito", "quiero", "y", "con"}:
            break

    num_m = re.search(r"\b(\d+)\b", clause[:kw_pos])
    if num_m:
        try:
            return int(num_m.group(1))
        except ValueError:
            pass

    return 1


def parse_presupuesto_items(text: str, inventario=None) -> list:
    """
    Identifica de forma determinística los productos solicitados y sus cantidades
    a partir del inventario oficial de 10 insumos con Stock Ilimitado.
    """
    if inventario is None:
        inventario = get_inventario()

    text_norm = normalize_text(text)
    clauses = re.split(r"[,;\n\+]|\s+y\s+|\s+e\s+|\s+ademas\s+|\s+tambien\s+", text_norm)

    found_items = []
    seen_ids = set()

    for clause in clauses:
        cl = clause.strip()
        if not cl:
            continue

        for item in inventario:
            item_id = item.get("id")
            if item_id in seen_ids:
                continue

            kws = PRODUCT_KEYWORDS.get(item_id, [normalize_text(item.get("producto", ""))])
            matched = False
            best_pos = -1
            for kw in sorted(kws, key=len, reverse=True):
                kw_norm = normalize_text(kw)
                m = re.search(r"\b" + re.escape(kw_norm) + r"\b", cl)
                if m:
                    matched = True
                    best_pos = m.start()
                    break

            if matched:
                qty = extract_quantity_near_keyword(cl, best_pos)
                pu = float(item.get("precio_unitario", 0))
                display_name = PRODUCT_DISPLAY_NAMES.get(item_id, item.get("producto", ""))
                found_items.append({
                    "id": item_id,
                    "producto": item.get("producto"),
                    "display": display_name,
                    "presentacion": item.get("presentacion"),
                    "cantidad": qty,
                    "precio_unitario": pu,
                    "subtotal": qty * pu,
                })
                seen_ids.add(item_id)

    if not found_items:
        for item in inventario:
            item_id = item.get("id")
            if item_id in seen_ids:
                continue
            kws = PRODUCT_KEYWORDS.get(item_id, [normalize_text(item.get("producto", ""))])
            for kw in sorted(kws, key=len, reverse=True):
                kw_norm = normalize_text(kw)
                m = re.search(r"\b" + re.escape(kw_norm) + r"\b", text_norm)
                if m:
                    kw_pos = m.start()
                    qty = extract_quantity_near_keyword(text_norm, kw_pos)
                    pu = float(item.get("precio_unitario", 0))
                    display_name = PRODUCT_DISPLAY_NAMES.get(item_id, item.get("producto", ""))
                    found_items.append({
                        "id": item_id,
                        "producto": item.get("producto"),
                        "display": display_name,
                        "presentacion": item.get("presentacion"),
                        "cantidad": qty,
                        "precio_unitario": pu,
                        "subtotal": qty * pu,
                    })
                    seen_ids.add(item_id)
                    break

    return found_items


# -----------------------------------------------------------------------------
# DETECCIÓN DE INTENCIONES CONVERSACIONALES
# -----------------------------------------------------------------------------

def strip_greeting_prefix(text: str) -> tuple[bool, str]:
    """
    Detecta si el mensaje comienza con un saludo o cortesía.
    Devuelve (has_greeting, remainder_text).
    """
    norm = normalize_text(text).strip()
    greetings = [
        "hola como estas", "hola que tal", "buenos dias", "buenas tardes", "buenas noches",
        "buen dia", "hola", "buenas", "que tal", "saludos"
    ]
    for g in sorted(greetings, key=len, reverse=True):
        if norm == g:
            return True, ""
        pattern = r"^\s*" + re.escape(g) + r"[\s,\.\!\?\:\;–—-]*"
        m = re.match(pattern, norm)
        if m:
            orig_match = re.match(r"^\s*" + re.escape(g) + r"[\s,\.\!\?\:\;–—-]*", text, re.IGNORECASE)
            if orig_match:
                rem = text[orig_match.end():].strip()
            else:
                rem = text[m.end():].strip()
            return True, rem
    return False, text.strip()


def is_greeting(text: str) -> bool:
    """Detecta saludos y fórmulas de cortesía puras."""
    has_g, rem = strip_greeting_prefix(text)
    if not has_g:
        return False
    norm_rem = normalize_text(rem).strip()
    return not rem or norm_rem in ["como estas", "que tal", "como te va", "todo bien", ""]


def is_thanks(text: str) -> bool:
    """Detecta agradecimientos."""
    norm = normalize_text(text).strip()
    thanks_list = ["gracias", "muchas gracias", "mil gracias", "te agradezco", "muchisimas gracias"]
    return norm in thanks_list or any(norm.startswith(t + " ") for t in thanks_list)


def is_how_are_you(text: str) -> bool:
    """Detecta preguntas de estado como '¿cómo estás?'."""
    norm = normalize_text(text).strip()
    return any(p in norm for p in ["como estas", "como te va", "como andas", "todo bien"])


def has_negative_budget_constraint(text: str) -> bool:
    """
    Detecta explícitamente si el usuario solicitó NO armar o posponer un presupuesto:
    - 'pero todavía no hagas un presupuesto'
    - 'no hagas presupuesto'
    - 'sin presupuesto'
    - 'solo quiero saber el precio'
    - 'no quiero un presupuesto'
    """
    norm = normalize_text(text).strip()
    triggers = [
        "no hagas un presupuesto", "no hagas presupuesto", "no hacer un presupuesto",
        "no hacer presupuesto", "todavia no hagas un presupuesto", "todavia no hagas presupuesto",
        "pero todavia no hagas un presupuesto", "pero todavia no hagas presupuesto",
        "pero no hagas presupuesto", "pero no hagas un presupuesto",
        "sin hacer un presupuesto", "sin hacer presupuesto", "sin presupuesto",
        "no quiero un presupuesto", "no quiero presupuesto", "no armes un presupuesto",
        "no armes presupuesto", "no armar presupuesto", "no preparar presupuesto",
        "no me hagas presupuesto", "no me hagas un presupuesto",
        "solo quiero saber el precio", "solo saber el precio", "solo consultar el precio",
        "solo consultar precio", "solo el precio", "solo saber el costo", "solo consultar"
    ]
    return any(t in norm for t in triggers)


def is_budget_pause(text: str) -> bool:
    """Detecta intención de pausar o posponer el presupuesto."""
    norm = normalize_text(text).strip()
    triggers = [
        "deja el presupuesto en pausa", "dejar en pausa", "en pausa", "pausa el presupuesto",
        "pausar el presupuesto", "dejemos en pausa", "dejalo en pausa", "pone en pausa",
        "dejemos el presupuesto para despues", "dejemos el presupuesto", "despues vemos el presupuesto",
        "luego seguimos con el presupuesto", "dejemos esto para despues"
    ]
    return any(t in norm for t in triggers)


def is_change_topic(text: str) -> bool:
    """Detecta la intención explícita de cambiar de tema o posponer el presupuesto en curso."""
    norm = normalize_text(text).strip()
    if is_budget_pause(text):
        return True
    triggers = [
        "dejemos el presupuesto para despues", "dejemos el presupuesto", "despues vemos el presupuesto",
        "luego seguimos con el presupuesto", "dejemos esto para despues", "dejemos eso",
        "quiero preguntarte otra cosa", "te consulto otra cosa", "te pregunto otra cosa",
        "otra cosa", "otro tema", "cambiar de tema", "cambiemos de tema", "hablemos de otra cosa",
        "tengo otra consulta", "otra pregunta", "despues seguimos", "luego seguimos",
        "despues lo vemos", "olvidate de eso", "otra duda", "te hago otra pregunta"
    ]
    return any(t in norm for t in triggers)


def is_system_help(text: str) -> bool:
    """Detecta solicitudes para conocer las capacidades del panel y del asistente."""
    norm = normalize_text(text).strip()
    triggers = [
        "que podes hacer", "que podes hacer vos", "que haces", "que hace este panel",
        "como funciona", "que funciones tenes", "cuales son tus funciones", "que herramientas tenes",
        "en que me podes ayudar", "para que servis", "que sabes hacer", "ayuda",
        "como uso el panel", "como se usa", "que puedo hacer aca", "manual de uso",
        "explicame como funciona", "guia del sistema", "que opciones tengo"
    ]
    return any(t in norm for t in triggers)


def is_payment_methods_query(text: str) -> bool:
    """Detecta consultas informativas sobre medios de pago aceptados por UMSA."""
    norm = normalize_text(text).strip()
    triggers = [
        "medios de pago", "formas de pago", "metodos de pago", "medio de pago",
        "que medios de pago acepta umsa", "que medios de pago aceptan", "que medios de pago tienen",
        "que medios de pago hay", "como se puede pagar", "como puedo pagar", "como pago", "como pagar",
        "aceptan transferencia", "aceptan transferencias", "aceptan tarjeta", "aceptan tarjetas",
        "aceptan mercado pago", "aceptan mercadopago", "tienen mercadopago", "cobran en efectivo",
        "puedo pagar con transferencia", "puedo pagar con mercado pago", "puedo pagar con tarjeta",
        "datos bancarios", "cbu de umsa", "alias de umsa", "cuenta bancaria", "como cobrar"
    ]
    return any(t in norm for t in triggers)


def is_inventory_catalog_query(text: str) -> bool:
    """Detecta solicitudes del listado o catálogo general de insumos descartables."""
    norm = normalize_text(text).strip()
    triggers = [
        "que productos tienen disponibles", "que insumos tienen disponibles", "que productos hay disponibles",
        "que insumos tenemos", "que insumos hay", "que productos tenemos", "que productos hay",
        "que materiales tenemos", "que materiales hay", "cuales son los insumos", "cuales son los productos",
        "catalogo de insumos", "catalogo de productos", "catalogo", "ver inventario",
        "mostrar inventario", "lista de precios", "listado de precios", "insumos disponibles",
        "productos disponibles", "materiales disponibles", "que tienen", "que venden",
        "que cosas tienen", "mostrame los insumos", "que insumos medicos hay", "que insumos medicos tienen"
    ]
    has_noun = any(w in norm for w in ["insumo", "insumos", "producto", "productos", "material", "materiales", "catalogo", "inventario"])
    has_query = any(w in norm for w in ["que", "cuales", "tienen", "hay", "disponible", "disponibles", "mostrar", "ver", "lista", "listado"])
    is_price = any(w in norm for w in ["cuanto cuesta", "cuanto cuestan", "cuanto sale", "cuanto salen", "que precio"])
    return (any(t in norm for t in triggers) or (has_noun and has_query)) and not is_price


def is_price_inquiry(text: str) -> bool:
    """
    Detecta consultas de precio unitario o costo de insumos específicos sin crear presupuestos.
    Ej: '¿Cuánto cuestan los guantes?', '¿Cuánto sale el alcohol?', '¿Y cuánto cuesta la caja de jeringas?'
    """
    if has_negative_budget_constraint(text):
        return True
    norm = normalize_text(text).strip()
    if is_budget_initiation_intent(norm):
        return False
    price_words = [
        "cuanto cuesta", "cuanto cuestan", "cuanto sale", "cuanto salen",
        "que precio tiene", "que precio tienen", "precio de", "precios de",
        "valor de", "cuanto me saldria", "cuanto saldrian", "cuanto costaria",
        "que valor tienen", "a cuanto estan", "a cuanto tienen",
        "costo de", "costo", "precio", "valor", "tarifa", "saber el costo", "saber el precio"
    ]
    return any(pw in norm for pw in price_words)


def is_budget_initiation_intent(text: str) -> bool:
    """
    Detecta ÚNICAMENTE la intención explícita de armar, emitir o preparar una cotización/presupuesto.
    Respeta cualquier restricción negativa solicitada por el usuario.
    """
    if has_negative_budget_constraint(text):
        return False
    norm = normalize_text(text).strip()
    budget_verbs = [
        "necesito preparar un presupuesto", "preparar un presupuesto", "preparar presupuesto",
        "presupuesto para", "presupuesto de", "presupuestar", "presupuestame",
        "hacer un presupuesto", "hacer presupuesto", "crear un presupuesto", "crear presupuesto",
        "armar un presupuesto", "armar presupuesto", "emitir un presupuesto", "emitir presupuesto",
        "generar presupuesto", "generar un presupuesto", "haceme un presupuesto", "necesito un presupuesto",
        "necesito presupuesto", "quiero un presupuesto", "quiero presupuesto", "cotizacion",
        "cotizar", "cotizame", "hacer una cotizacion", "hacer cotizacion", "armar una cotizacion",
        "armar cotizacion", "preparar una cotizacion", "preparar cotizacion", "necesito una cotizacion",
        "necesito cotizacion", "quiero cotizar", "necesito cotizar"
    ]
    return any(v in norm for v in budget_verbs)


def is_direct_product_demand(text: str) -> bool:
    """
    Detecta peticiones directas de productos como:
    - 'Quiero cuatro cajas de guantes'
    - 'Necesito 2 cajas de jeringas'
    - '4 cajas de guantes'
    """
    if has_negative_budget_constraint(text):
        return False
    if is_price_inquiry(text):
        return False
    norm = normalize_text(text).strip()
    items = parse_presupuesto_items(text)
    if not items:
        return False
    direct_starters = ["quiero", "necesito", "dame", "mandame", "solicito", "pedir", "cargar", "anotar"]
    if any(norm.startswith(s + " ") for s in direct_starters):
        return True
    words = norm.split()
    if words and (words[0].isdigit() or words[0] in NUMBER_WORDS):
        return True
    return False


def is_budget_resume(text: str) -> bool:
    """Detecta intención de retomar o consultar el estado de un borrador de presupuesto en curso."""
    norm = normalize_text(text).strip()
    triggers = [
        "volvamos al presupuesto de antes", "volver al presupuesto de antes", "retomemos el presupuesto de antes",
        "volvamos al presupuesto anterior", "volver al presupuesto anterior", "retomemos el presupuesto anterior",
        "retomemos el presupuesto", "retomar el presupuesto", "retomar presupuesto",
        "continuar el presupuesto", "continuemos con el presupuesto", "sigamos con el presupuesto",
        "seguir con el presupuesto", "en que quedo el presupuesto", "como quedo el presupuesto",
        "volver al presupuesto", "volvamos al presupuesto", "retomar lo anterior", "sigamos con lo anterior",
        "volvamos a lo anterior", "retomemos", "revisemos el presupuesto", "volver al borrador"
    ]
    return any(t in norm for t in triggers)


def is_confirmation(text: str) -> bool:
    """Detecta confirmación explícita para generar el presupuesto y emitir el PDF."""
    norm = normalize_text(text).strip()
    direct = [
        "si", "confirmo", "confirmado", "generar", "genera", "generalo", "aceptar",
        "dale", "ok", "correcto", "de acuerdo", "proceder", "adelante", "crear",
        "emitir", "listo", "hacelo", "esta bien", "esta perfecto"
    ]
    if norm in direct:
        return True
    phrases = [
        "si confirmo", "si confirma", "confirmar presupuesto", "confirmo el presupuesto",
        "genera el pdf", "generar el pdf", "generar pdf", "genera pdf", "quiero el pdf",
        "si genera el pdf", "si generalo", "si confirmalo", "confirmalo",
        "confirmalo y genera el pdf", "si confirmalo y genera el pdf",
        "emitir presupuesto", "dale generalo", "de acuerdo generalo",
        "crear presupuesto", "hacer el pdf", "esta bien generalo",
        "si quiero el pdf", "si por favor"
    ]
    return any(p in norm for p in phrases)


def is_cancellation(text: str) -> bool:
    """Detecta cancelación del flujo de presupuesto."""
    norm = normalize_text(text).strip()
    direct = ["cancelar", "cancela", "cancelalo", "anular", "anula", "salir", "basta", "dejalo"]
    if norm in direct:
        return True
    phrases = [
        "cancela el presupuesto", "cancelar presupuesto", "no quiero el presupuesto",
        "no lo quiero", "no quiero nada", "no quiero ese presupuesto", "no deseo continuar",
        "volver atras", "volvamos atras", "olvidalo", "dejalo sin efecto", "anular el presupuesto"
    ]
    return any(p in norm for p in phrases)


def is_total_inquiry(text: str) -> bool:
    """Detecta preguntas sobre el total o costo acumulado en un presupuesto."""
    norm = normalize_text(text).strip()
    phrases = [
        "cuanto queda", "cuanto es el total", "cual es el total", "cuanto va",
        "como quedo", "como queda", "cuanto costaria eso", "cuanto me costaria eso",
        "cuanto sale todo junto", "cuanto seria", "cuanto me saldria",
        "que total da", "cuanto suma", "pasame el total", "cual seria el total",
        "cuanto es", "cuanto saldria esto", "cual es el total ahora", "cuanto va ahora"
    ]
    return any(p in norm for p in phrases)


def is_hypothetical_remove_intent(text: str) -> tuple[bool, int | None]:
    """Detecta preguntas hipotéticas como '¿Cuánto queda si saco el alcohol?'."""
    norm = normalize_text(text).strip()
    is_hypo = any(h in norm for h in ["si saco", "si quito", "si retiro", "si elimino", "sin el", "sin la", "sin los", "sin las"])
    is_inq = any(q in norm for q in ["cuanto queda", "cuanto es", "cual es el total", "cuanto seria", "cuanto sale", "que total"])
    if is_hypo and is_inq:
        prod_id = detect_product_id(norm)
        return True, prod_id
    return False, None


def is_add_more_intent(text: str) -> tuple[bool, int | None, int]:
    """
    Detecta solicitudes de sumar unidades adicionales como:
    - 'Necesito otras dos cajas más'
    - 'Agregá 3 más'
    - 'Sumá 2 cajas más'
    """
    norm = normalize_text(text).strip()
    has_more = any(w in norm for w in ["mas", "adicional", "adicionales", "otra", "otras", "otro", "otros"])
    has_verb = any(t in norm for t in ["agrega", "agrego", "suma", "sumar", "pone", "ponele", "incorpor", "necesito", "quiero", "cargar", "dame"])
    is_direct_qty_more = bool(re.search(r"\b(?:\d+|un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s+(?:cajas?|paquetes?|rollos?|frascos?|unidades?)?\s*mas\b", norm))
    is_other_qty = bool(re.search(r"\botras?\s+(?:\d+|un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\b", norm))

    if not (has_more and (has_verb or is_direct_qty_more or is_other_qty)):
        return False, None, 0

    prod_id = detect_product_id(norm)
    qty = 1

    m_num = re.search(r"\b(\d+)\s+mas\b", norm)
    if not m_num:
        m_num = re.search(r"\botras?\s+(\d+)\b", norm)
    if not m_num:
        m_num = re.search(r"\b(\d+)\s+(?:cajas?|paquetes?|rollos?|unidades?|frascos?)", norm)

    if m_num:
        try:
            qty = int(m_num.group(1))
        except ValueError:
            qty = 1
    else:
        for w, val in sorted(NUMBER_WORDS.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(r"\b" + re.escape(w) + r"\s+(?:cajas?|paquetes?|rollos?|unidades?|frascos?)?\s*mas\b", norm):
                qty = val
                break
            if re.search(r"\botras?\s+" + re.escape(w) + r"\b", norm):
                qty = val
                break

    return True, prod_id, qty


def handle_uncatalogued_product_inquiry(text: str, inventario=None) -> str | None:
    """
    Detecta si el usuario está consultando o cotizando un insumo o equipo médico
    que NO está presente en el inventario oficial de 10 insumos descartables.
    """
    if inventario is None:
        inventario = get_inventario()

    if detect_product_id(text) is not None:
        return None

    norm = normalize_text(text)
    uncatalogued_terms = [
        "tensiometro", "ecografo", "termometro", "estetoscopio", "oximetro", "saturometro",
        "bisturi", "sutura", "cateter", "suero", "venda", "vendas", "aguja", "agujas",
        "nebulizador", "electrocardiografo", "camilla", "silla de ruedas", "respirador",
        "mascarilla n95", "guantes de nitrilo", "latex quirurgico", "desfibrilador",
        "guante quirurgico", "otoscopio", "laringoscopio"
    ]

    matched_uncatalogued = None
    for term in uncatalogued_terms:
        if re.search(r"\b" + re.escape(term) + r"\b", norm):
            matched_uncatalogued = term
            break

    if extract_client_name(text) is not None and is_budget_initiation_intent(text):
        return None

    if matched_uncatalogued or (is_price_inquiry(text) and not parse_presupuesto_items(text)):
        prod_ref = f"'{matched_uncatalogued}'" if matched_uncatalogued else "el insumo o equipo solicitado"
        lines = [
            f"El producto {prod_ref} no se encuentra disponible en nuestro catálogo oficial de insumos descartables de UMSA Centro Médico.\n",
            "Actualmente disponemos de **Stock ILIMITADO** con disponibilidad permanente para los siguientes 10 insumos médicos oficiales:\n",
        ]
        for it in inventario:
            lines.append(f"• **{it['producto']}** ({it['presentacion']}): **${it['precio_unitario']}**")
        lines.append("\n¿Deseás realizar una consulta de precios o preparar un presupuesto sobre alguno de estos insumos?")
        return "\n".join(lines)

    return None


def is_remove_item_intent(text: str) -> tuple[bool, int | None]:
    """Detecta intención de quitar un producto del presupuesto actual."""
    norm = normalize_text(text).strip()
    remove_triggers = [
        "quita", "quite", "quitar", "saca", "saque", "sacar", "elimina", "elimine", "eliminar",
        "borra", "borre", "borrar", "no quiero", "sin los", "sin las", "sin el",
        "remover", "retirar", "retira", "retire"
    ]
    if not any(t in norm for t in remove_triggers):
        return False, None
    prod_id = detect_product_id(norm)
    return True, prod_id


def is_modify_quantity_intent(text: str) -> tuple[bool, int | None, int | None]:
    """Detecta cambio de cantidad de un producto en el presupuesto actual."""
    norm = normalize_text(text).strip()
    modify_triggers = [
        "cambia", "cambie", "cambiar", "modifica", "modifique", "modificar",
        "pone", "ponga", "poner", "que sean", "en lugar de", "en vez de"
    ]
    if not any(t in norm for t in modify_triggers):
        return False, None, None

    prod_id = detect_product_id(norm)
    if not prod_id:
        return False, None, None

    m_instead = re.search(r"(?:en\s+vez\s+de|en\s+lugar\s+de)\s+(\d+|\w+).*?(?:quiero|pone|ponele|deja|que\s+sean|a)\s+(\d+|\w+)", norm)
    if m_instead:
        new_raw = m_instead.group(2)
        if new_raw.isdigit():
            return True, prod_id, int(new_raw)
        if new_raw in NUMBER_WORDS:
            return True, prod_id, NUMBER_WORDS[new_raw]

    m_a = re.search(r"(?:a\s+|que\s+sean\s+|ponele\s+|pone\s+)(\d+)", norm)
    if m_a:
        return True, prod_id, int(m_a.group(1))

    for w, val in NUMBER_WORDS.items():
        if re.search(r"(?:a\s+|que\s+sean\s+|ponele\s+|pone\s+)" + re.escape(w) + r"\b", norm):
            return True, prod_id, val

    m_end = re.search(r"(?:cambia|modifica).*?(\d+)", norm)
    if m_end:
        return True, prod_id, int(m_end.group(1))

    return False, None, None


# -----------------------------------------------------------------------------
# BASE DE CONOCIMIENTO MÉDICO Y GENERAL
# -----------------------------------------------------------------------------

def handle_definition_or_medical_inquiry(text: str) -> str | None:
    """
    Responde consultas de definición y utilidad de insumos médicos descartables.
    Ej: '¿Qué es una gasa?', '¿Para qué sirven las cofias?', '¿Qué es el agua oxigenada?'
    """
    norm = normalize_text(text)

    if "gasa" in norm and any(w in norm for w in ["que es", "para que sirve", "definicion", "funcion"]):
        return (
            "Una **gasa médica** es un tejido fino, estéril o limpio, confeccionado en algodón hidrófilo. "
            "Se utiliza comúnmente en curaciones, apósitos, absorción de fluidos y protección de heridas o lesiones dérmicas. "
            "En UMSA disponemos de **Rollo de gasa (90 cm x 100 m)** a **$1.200** con disponibilidad permanente y **Stock ILIMITADO**."
        )

    if "guante" in norm and any(w in norm for w in ["que es", "para que sirve", "que son", "definicion"]):
        return (
            "Los **guantes de látex descartables** son elementos de protección y bioseguridad indispensables "
            "para prevenir la contaminación cruzada entre profesionales y pacientes en consultas, curaciones e intervenciones. "
            "En UMSA disponemos de **Cajas x 100 unidades** a **$2.500** con **Stock ILIMITADO**."
        )

    if "jeringa" in norm and any(w in norm for w in ["que es", "para que sirve", "que son", "definicion"]):
        return (
            "Las **jeringas descartables** son instrumentos sanitarios estériles de un solo uso diseñados para "
            "la administración precisa de medicamentos parenterales o la aspiración de líquidos biológicos. "
            "En UMSA disponemos de **Cajas x 50 unidades** a **$3.500** con **Stock ILIMITADO**."
        )

    if "algodon" in norm and any(w in norm for w in ["que es", "para que sirve", "definicion"]):
        return (
            "El **algodón hidrófilo** es una fibra altamente absorbente purificada utilizada en antisepsia tópica "
            "previo a punciones o inyecciones, y para la higiene y protección en curaciones superficiales. "
            "En UMSA disponemos de **Paquetes de 200 g** a **$1.000** con **Stock ILIMITADO**."
        )

    if "alcohol" in norm and any(w in norm for w in ["que es", "para que sirve", "definicion"]):
        return (
            "El **alcohol antiséptico** (etanol al 70%) es un desinfectante tópico eficaz para la eliminación rápida "
            "de bacterias y virus en piel intacta, manos y áreas de preparación médica. "
            "En UMSA disponemos de **Frascos de 100 ml** a **$3.000** con **Stock ILIMITADO**."
        )

    if "oxigenada" in norm and any(w in norm for w in ["que es", "para que sirve", "definicion"]):
        return (
            "El **agua oxigenada** (peróxido de hidrógeno a 10 volúmenes) actúa como desinfectante suave y desbridante "
            "químico para la limpieza mecánica de heridas, facilitando la remoción de exudados y vendajes adheridos. "
            "En UMSA disponemos de **Frascos de 100 ml** a **$3.000** con **Stock ILIMITADO**."
        )

    if any(w in norm for w in ["barbijo", "mascarilla", "tapaboca"]) and any(w in norm for w in ["que es", "para que sirve", "que son", "definicion"]):
        return (
            "Los **barbijos descartables** son mascarillas de triple capa con ajuste nasal y elástico que filtran "
            "microgotas y aerosoles para proteger las vías respiratorias en consultorios y áreas clínicas. "
            "En UMSA disponemos de **Cajas x 50 unidades** a **$2.500** con **Stock ILIMITADO**."
        )

    if any(w in norm for w in ["cinta", "micropore"]) and any(w in norm for w in ["que es", "para que sirve", "definicion"]):
        return (
            "La **cinta adhesiva hipoalergénica** (tipo micropore) es una cinta de papel poroso y respirable que "
            "fija apósitos, gasas o tubuladuras sobre la piel sin provocar irritaciones ni dejar residuos al despegarla. "
            "En UMSA disponemos de **Rollos x 1 unidad** a **$1.500** con **Stock ILIMITADO**."
        )

    if "cofia" in norm and any(w in norm for w in ["que es", "para que sirve", "que son", "definicion"]):
        return (
            "Las **cofias descartables** son gorros plisados de tela no tejida diseñados para cubrir el cabello "
            "del personal sanitario y mantener el control higiénico en quirófanos y consultorios. "
            "En UMSA disponemos de **Paquetes x 100 unidades** a **$3.000** con **Stock ILIMITADO**."
        )

    if "camisolin" in norm and any(w in norm for w in ["que es", "para que sirve", "que son", "definicion"]):
        return (
            "Los **camisolines descartables** son batas hidrorrepelentes de polipropileno no tejido que "
            "brindan una barrera protectora estéril frente a salpicaduras y fluidos en procedimientos médicos. "
            "En UMSA disponemos de **Paquetes x 10 unidades** a **$8.000** con **Stock ILIMITADO**."
        )

    return None


def handle_general_knowledge_or_question(text: str) -> str | None:
    """
    Responde consultas de cultura general básica o aclara el alcance del asistente.
    Ej: '¿Cuál es la capital de Francia?', '¿Dónde queda UMSA?'
    """
    norm = normalize_text(text)

    # Capital de Francia
    if "capital" in norm and "francia" in norm:
        return (
            "La capital de Francia es **París**.\n\n"
            "Como asistente administrativo de UMSA Centro Médico, mi ámbito principal de asistencia son los insumos sanitarios, "
            "presupuestos oficiales y medios de pago, pero con gusto responderé cualquier consulta general que tengas."
        )

    # Otras capitales comunes
    if "capital" in norm and ("argentina" in norm or "buenos aires" in norm):
        return "La capital de la República Argentina es la **Ciudad Autónoma de Buenos Aires**."
    if "capital" in norm and "espana" in norm:
        return "La capital de España es **Madrid**."
    if "capital" in norm and "italia" in norm:
        return "La capital de Italia es **Roma**."
    if "capital" in norm and ("eeuu" in norm or "estados unidos" in norm):
        return "La capital de los Estados Unidos es **Washington D.C.**."
    if "capital" in norm and "uruguay" in norm:
        return "La capital de la República Oriental del Uruguay es **Montevideo**."
    if "capital" in norm and "chile" in norm:
        return "La capital de Chile es **Santiago de Chile**."
    if "capital" in norm and "brasil" in norm:
        return "La capital de Brasil es **Brasilia**."

    # Horarios de UMSA
    if any(w in norm for w in ["horario", "horarios", "a que hora"]) and any(w in norm for w in ["atencion", "abren", "atienden", "umsa"]):
        return (
            "El Centro Médico UMSA atiende de **lunes a viernes de 08:00 a 20:00** y los **sábados de 08:00 a 13:00**. "
            "Para consultas sobre turnos o agendas de profesionales, podés consultar el módulo de turnos."
        )

    return None


# -----------------------------------------------------------------------------
# GENERADORES DE RESPUESTAS ESTRUCTURADAS
# -----------------------------------------------------------------------------

def handle_payment_methods_query() -> str:
    """Genera una respuesta completa y profesional sobre los medios de pago aceptados."""
    from .pagos import get_medios_pago
    medios = get_medios_pago()

    lines = [
        "💳 **Medios de Pago Oficiales de UMSA Centro Médico:**\n",
        "En UMSA aceptamos cuatro medios de pago oficiales, con control administrativo y vinculación directa a presupuestos:\n"
    ]
    for m in medios:
        estado_badge = "✅ Habilitado" if m.get("activo") else "⏸️ Inactivo temporalmente"
        lines.append(f"• **{m['icono']} {m['nombre']}** ({estado_badge})")
        lines.append(f"  {m['descripcion']}")
        if m.get("instrucciones"):
            lines.append(f"  *Instrucciones:* {m['instrucciones']}")
        if m.get("codigo") == "transferencia" and m.get("datos_bancarios"):
            db = m["datos_bancarios"]
            banco = db.get("banco") or "A configurar"
            titular = db.get("titular") or "Centro Médico UMSA"
            cbu = db.get("cbu") or "Pendiente de configuración"
            alias = db.get("alias") or "Pendiente de configuración"
            lines.append(f"  *Datos bancarios:* Banco: {banco} | Titular: {titular} | CBU: {cbu} | Alias: {alias}")
        lines.append("")

    lines.append("🎁 **Promociones, Billeteras y Tarjetas Habilitadas:**")
    lines.append("• **Naranja X:** Plan Z con 3 cuotas cero interés en todas las prestaciones y compras.")
    lines.append("• **Mercado Pago:** 15% de ahorro con dinero en cuenta y QR dinámico en mostrador.")
    lines.append("• **Visa y Mastercard:** Cuota Simple en 3 y 6 pagos para tarjetas bancarias.")
    lines.append("• **MODO y Cuenta DNI:** 20% de reintegro en salud con bancos adheridos.")
    lines.append("• **Efectivo y Transferencia:** 10% de bonificación directa por pronto pago.")
    lines.append("")
    lines.append("📌 **Gestión de Cobranzas y Presupuestos:**")
    lines.append("Cada pago se registra de forma manual o verificada vinculándolo al número de presupuesto oficial, lo que permite calcular automáticamente el importe pagado, el saldo pendiente y los estados (Pendiente, Parcial, Pagado o Cancelado) en la sección **Medios de pago** del panel.")
    return "\n".join(lines)


def handle_system_help_query() -> str:
    """Genera una explicación amplia, profesional y estructurada de todas las funciones del sistema."""
    from .services import get_inventario
    inv_count = len(get_inventario())

    return (
        "🏥 **Panel Administrativo Inteligente de UMSA Centro Médico**\n\n"
        "Como asistente administrativo del centro médico, puedo orientarte y asistirte de forma integral en las siguientes áreas:\n\n"
        "1. 📦 **Catálogo de Insumos Médicos:**\n"
        f"   • Disponemos de **{inv_count} insumos descartables oficiales** (guantes de látex, jeringas, rollos de gasa, algodón, alcohol antiséptico, agua oxigenada, barbijos descartables, cinta micropore, cofias y camisolines).\n"
        "   • Todos los productos cuentan con **Stock ILIMITADO** permanente, fotografías individuales y precios oficiales actualizados.\n"
        "   • Podés consultarme disponibilidad, presentaciones y precios unitarios en cualquier momento.\n\n"
        "2. 📋 **Presupuestos y Cotizaciones en PDF:**\n"
        "   • Creación bajo demanda de presupuestos oficiales para médicos, clínicas o instituciones.\n"
        "   • Cálculos matemáticos rigurosos (subtotal, IVA opcional y total), numeración oficial correlativa (`UMSA-P-YYYY-XXXX`) y descarga física directa en PDF con ReportLab.\n"
        "   • Flujo interactivo: podés agregar, quitar o modificar insumos con lenguaje natural antes de confirmar la emisión.\n\n"
        "3. 💳 **Medios de Pago y Cobranzas:**\n"
        "   • Administración de los 4 medios de pago: Efectivo, Tarjeta de débito/crédito, Transferencia bancaria y Mercado Pago.\n"
        "   • Registro de pagos asociado a presupuestos, cálculo automático de saldo pendiente y control de estados (Pendiente, Parcial, Pagado o Cancelado).\n\n"
        "4. 📊 **Dashboard e Historiales Persistentes:**\n"
        "   • Métricas en tiempo real de presupuestos emitidos y cobranzas confirmadas.\n"
        "   • Historial completo con filtros por estado, cliente o fecha.\n\n"
        "5. 🗄️ **Almacenamiento Local Físico (`files_storage/`):**\n"
        "   • Módulos organizados de turnos, pacientes, profesionales, especialidades, administración y pagos.\n"
        "   • Auto-indexación en `INDEX.md` y registro de directivas permanentes en `MEMORY.md`.\n\n"
        "¿En qué te gustaría colaborar hoy?"
    )


def handle_inventory_query(text: str, inventario=None) -> str | None:
    """
    Responde consultas de catálogo completo, disponibilidad o presentación de insumos.
    """
    if inventario is None:
        inventario = get_inventario()

    norm = normalize_text(text)

    # 1. Catálogo o listado general de insumos disponibles
    if is_inventory_catalog_query(text):
        lines = ["📦 **Catálogo Oficial de Insumos Médicos UMSA (Stock Ilimitado):**\n"]
        for p in inventario:
            lines.append(
                f"• **{p['producto']}** — Presentación: {p['presentacion']} — "
                f"Precio: **${p['precio_unitario']}** — Stock: **ILIMITADO**"
            )
        lines.append("\nTodos los insumos tienen disponibilidad permanente garantizada.")
        lines.append("Si necesitás preparar un presupuesto formal en PDF, solo avisame indicando los insumos y cantidades.")
        return "\n".join(lines)

    # 2. Presentación específica
    if any(w in norm for w in ["presentacion", "formato", "tamano", "medida"]):
        prod_id = detect_product_id(norm)
        if prod_id:
            item = next((it for it in inventario if it["id"] == prod_id), None)
            if item:
                return (
                    f"La presentación oficial de **{item['producto']}** es **{item['presentacion']}** "
                    f"y su precio oficial es **${item['precio_unitario']}** con **Stock ILIMITADO**."
                )

    # 3. Disponibilidad / Stock ("¿Hay guantes?", "¿Tienen alcohol?")
    if any(w in norm for w in ["hay", "tienen", "tenes", "disponen", "stock", "quedan"]):
        prod_id = detect_product_id(norm)
        if prod_id:
            item = next((it for it in inventario if it["id"] == prod_id), None)
            if item:
                disp = PRODUCT_DISPLAY_NAMES.get(item["id"], item["producto"])
                return (
                    f"Sí, contamos con **{disp}** a **${item['precio_unitario']}** con disponibilidad permanente y **Stock ILIMITADO**."
                )

    return None


def handle_price_inquiry_query(text: str, inventario=None, draft=None) -> str:
    """
    Responde consultas de precios con exactitud, stock ilimitado y tono profesional,
    SIN iniciar un presupuesto ni solicitar datos de cliente.
    Si hay un borrador de presupuesto en curso, ofrece incorporarlo contextualmente.
    """
    if inventario is None:
        inventario = get_inventario()

    items = parse_presupuesto_items(text, inventario)
    if items:
        lines = []
        for it in items:
            pu = int(it["precio_unitario"])
            cant = int(it["cantidad"])
            if cant > 1:
                sub = int(it["subtotal"])
                lines.append(f"• **{it['display']}**: ${pu} por unidad (${sub} por las {cant} unidades). Stock: **ILIMITADO**.")
            else:
                lines.append(f"• **{it['display']}**: **${pu}** ({it['presentacion']}). Stock: **ILIMITADO**.")

        total = int(sum(it["subtotal"] for it in items))
        if len(items) > 1 or (len(items) == 1 and items[0]["cantidad"] > 1):
            lines.append(f"\nEl total estimado para esta consulta es de **${total}**.")

        if draft and draft.get("active"):
            cliente_ref = draft.get("cliente") or "el consultorio / cliente"
            lines.append(f"\n¿Querés que agregue este insumo al presupuesto en curso para **{cliente_ref}**?")
        else:
            lines.append("\nSi deseás preparar un presupuesto formal en PDF para un cliente o institución con estos insumos, solo pedímelo diciendo por ejemplo: *'Prepará un presupuesto para estos insumos'*.")
        return "\n".join(lines)
    else:
        norm = normalize_text(text)
        for item in inventario:
            if normalize_text(item.get("producto", "")) in norm or detect_product_id(norm) == item.get("id"):
                pu = int(item.get("precio_unitario", 0))
                disp = PRODUCT_DISPLAY_NAMES.get(item.get("id"), item.get("producto"))
                res = f"El precio oficial de **{disp}** es de **${pu}** con disponibilidad permanente y **Stock ILIMITADO**."
                if draft and draft.get("active"):
                    cliente_ref = draft.get("cliente") or "el consultorio / cliente"
                    res += f"\n\n¿Querés que lo incorpore al presupuesto para **{cliente_ref}**?"
                else:
                    res += "\n\nSi necesitás emitir un presupuesto formal en PDF, avisame y lo preparamos."
                return res

        return (
            "Los precios de nuestro catálogo oficial van desde $1.000 hasta $8.000 con Stock Ilimitado. "
            "Podés consultarme por un producto específico (ej: *'¿Cuánto cuestan los guantes de látex?'*) o pedirme el catálogo completo."
        )


# -----------------------------------------------------------------------------
# MOTOR CONVERSACIONAL CENTRAL (CON MEMORIA Y CONTROL DE INTENCIONES)
# -----------------------------------------------------------------------------

def process_conversational_message(
    message: str,
    budget_draft: dict | None,
    module: str = "",
    history: list | None = None
) -> tuple[str, dict | None, dict]:
    """
    Motor central conversacional de UMSA IA.
    Interpreta con precisión contextual y razonamiento semántico real las intenciones del usuario:
    - Saludos y cortesía con extracción limpia de contenido sustantivo.
    - Explicación amplia de funciones del panel administrativo.
    - Catálogo oficial de insumos médicos con Stock Ilimitado.
    - Consultas de precios sin crear presupuestos ni alterar borradores.
    - Respeto estricto a restricciones negativas ('pero todavía no hagas un presupuesto').
    - Presupuestos bajo demanda y pedidos directos de productos con cálculo de subtotales reales.
    - Continuación y modificación de presupuestos con adición relativa ('otras dos cajas más').
    - Detección precisa de nombres de clientes evitando confundir insumos o frases.
    - Pausa y reanudación de presupuestos con persistencia contextual sin notas molestas en mensajes no relacionados.
    - Aclaración informada de productos no catalogados sin inventar información ni precios.
    """
    meta = {}
    draft = budget_draft.copy() if budget_draft else None
    has_active_draft = draft is not None and draft.get("active", False)

    # 1. Analizar si hay saludo al inicio y aislar el contenido sustantivo
    has_greeting_prefix, remainder = strip_greeting_prefix(message)
    work_message = remainder if remainder else message
    norm_rem = normalize_text(remainder).strip()

    # Si es solo un saludo o fórmula de cortesía sin contenido operativo ("Hola", "Buenas", "Hola ¿cómo estás?")
    if has_greeting_prefix and (not remainder or (is_valid_person_or_client_name(remainder)[0] is False and norm_rem in ["como estas", "que tal", "como te va", "todo bien", ""])):
        reply = (
            "¡Hola! Te doy la bienvenida al Panel Administrativo de UMSA Centro Médico. "
            "Estoy a tu disposición para ayudarte a consultar insumos con stock ilimitado, "
            "preparar presupuestos oficiales en PDF, gestionar los medios de pago y cobranzas, "
            "o consultar archivos del sistema. ¿En qué puedo colaborar hoy?"
        )
        return reply, draft, meta

    # 2. Cancelación explícita
    if is_cancellation(work_message):
        if has_active_draft:
            return (
                "Presupuesto cancelado. Podés solicitar uno nuevo en cualquier momento o consultarme sobre insumos y medios de pago.",
                None,
                meta
            )
        return (
            "Operación cancelada. ¿En qué más puedo ayudarte?",
            None,
            meta
        )

    # 3. Pausar presupuesto / Preguntas compuestas
    if is_budget_pause(message) or (has_active_draft and any(t in normalize_text(message) for t in ["otra cosa", "otro tema", "cambiar de tema", "hablemos de otra cosa"])):
        if has_active_draft:
            draft["paused"] = True
            draft["awaiting_client"] = False

        parts = [p.strip() for p in re.split(r"[\.\;\n]|\?\s*|¿", message) if p.strip()]
        sub_query = ""
        for p in parts:
            if not is_budget_pause(p) and len(p) >= 3:
                sub_query = p
                break

        if sub_query:
            if is_payment_methods_query(sub_query):
                pay_reply = handle_payment_methods_query()
                if has_active_draft:
                    pay_reply += f"\n\n*(Tu borrador de presupuesto sigue pausado en segundo plano. Cuando quieras retomarlo, solo decime 'volver al presupuesto')*."
                return pay_reply, draft, meta

            def_reply = handle_definition_or_medical_inquiry(sub_query)
            if def_reply:
                if has_active_draft:
                    def_reply += f"\n\n*(Borrador de presupuesto pausado y guardado en segundo plano. Cuando quieras retomarlo, decime 'volver al presupuesto')*."
                return def_reply, draft, meta

            if is_price_inquiry(sub_query):
                pr_reply = handle_price_inquiry_query(sub_query, draft=draft)
                return pr_reply, draft, meta

            gen_reply = handle_general_knowledge_or_question(sub_query)
            if gen_reply:
                if has_active_draft:
                    gen_reply += f"\n\n*(Borrador guardado en segundo plano)*."
                return gen_reply, draft, meta

        if has_active_draft:
            return (
                "Presupuesto pausado. Podés consultarme sobre medios de pago, insumos médicos o cualquier área del sistema.\n\n"
                "*(Cuando quieras reanudarlo, solo decime 'volver al presupuesto')*.",
                draft,
                meta
            )
        return "¡Por supuesto! Decime qué consulta tenés y con gusto te respondo.", None, meta

    # 4. Retomar presupuesto en curso
    if is_budget_resume(work_message):
        if has_active_draft:
            draft["paused"] = False
            items = draft.get("items", [])
            client = draft.get("cliente", "")
            if items:
                tot_int = int(sum(it["subtotal"] for it in items))
                lines = ["Retomamos el presupuesto en curso:\n"]
                for it in items:
                    cant_int = int(it["cantidad"])
                    pu_int = int(it["precio_unitario"])
                    sub_int = int(it["subtotal"])
                    lines.append(f"• {cant_int} unidad(es) de {it['display']} a ${pu_int} c/u: ${sub_int}")
                lines.append(f"\nTotal: **${tot_int}**.")
                if not client:
                    draft["awaiting_client"] = True
                    lines.append("\n¿A nombre de qué cliente o profesional lo preparamos?")
                else:
                    lines.append("\n¿Confirmás el presupuesto para emitir el PDF oficial o deseás agregar algún otro insumo?")
                return "\n".join(lines), draft, meta
            else:
                lines = [f"Retomamos el presupuesto para **{client or 'el consultorio'}**."]
                lines.append("Actualmente no tiene insumos cargados. ¿Cuáles te gustaría incluir? (Por ejemplo: *'2 cajas de guantes y 3 cajas de jeringas'*).")
                return "\n".join(lines), draft, meta
        else:
            return (
                "Actualmente no tenés ningún borrador de presupuesto en curso. "
                "Podés solicitar uno diciendo por ejemplo: *'Quiero un presupuesto para 4 cajas de guantes'*.",
                None,
                meta
            )

    # 5. Restricción negativa explícita: "Quiero saber cuánto cuestan cuatro cajas de guantes, pero todavía no hagas un presupuesto"
    if has_negative_budget_constraint(work_message):
        items = parse_presupuesto_items(work_message)
        if items:
            lines = []
            for it in items:
                pu = int(it["precio_unitario"])
                cant = int(it["cantidad"])
                sub = int(it["subtotal"])
                if cant > 1:
                    lines.append(f"• **{it['display']}**: **${sub}** por las {cant} unidades (${pu} c/u). Stock: **ILIMITADO**.")
                else:
                    lines.append(f"• **{it['display']}**: **${pu}** ({it['presentacion']}). Stock: **ILIMITADO**.")
            tot = int(sum(it["subtotal"] for it in items))
            if len(items) > 1:
                lines.append(f"\nEl total es de **${tot}**.")
            lines.append("\nQueda registrado como consulta informativa sin generar presupuesto.")
            return "\n".join(lines), draft, meta

    # 6. Consulta de insumos no catalogados (ej: tensiómetros, ecógrafos)
    uncatalogued_reply = handle_uncatalogued_product_inquiry(work_message)
    if uncatalogued_reply:
        return uncatalogued_reply, draft, meta

    # 7. Definiciones de insumos médicos ("¿Qué es una gasa?")
    def_reply = handle_definition_or_medical_inquiry(work_message)
    if def_reply:
        return def_reply, draft, meta

    # 8. Medios de pago aceptados
    if is_payment_methods_query(work_message):
        return handle_payment_methods_query(), draft, meta

    # 9. Explicación de capacidades ("¿Qué podés hacer?")
    if is_system_help(work_message):
        return handle_system_help_query(), draft, meta

    # 10. Catálogo general de insumos, stock y disponibilidad
    inv_reply = handle_inventory_query(work_message)
    if inv_reply:
        return inv_reply, draft, meta

    # 11. Cultura general ("¿Cuál es la capital de Francia?")
    gen_reply = handle_general_knowledge_or_question(work_message)
    if gen_reply:
        return gen_reply, draft, meta

    # 12. Operaciones sobre borrador activo no pausado
    if has_active_draft and not draft.get("paused", False):
        # 12.1. Confirmación de emisión de PDF
        if is_confirmation(work_message):
            items = draft.get("items", [])
            client = draft.get("cliente", "").strip()
            if not items:
                return f"Todavía no agregaste insumos al presupuesto para **{client or 'el cliente'}**. Indicame qué insumos y qué cantidades querés cotizar.", draft, meta
            if not client:
                draft["awaiting_client"] = True
                return "Para emitir el PDF oficial solo falta el nombre del cliente o profesional. ¿A nombre de quién lo generamos?", draft, meta

            pdf_res = generate_presupuesto_pdf(
                cliente=client,
                productos=[{"descripcion": it["producto"], "cantidad": it["cantidad"], "precio_unitario": it["precio_unitario"]} for it in items],
                institucion="Centro Médico UMSA",
                observaciones="Presupuesto generado mediante panel administrativo interactivo.",
                validez="15 días corridos",
                iva_porcentaje=0.0,
            )
            tot_int = int(pdf_res["total"])
            try:
                append_memory(
                    f"Presupuesto {pdf_res['numero']} generado para {client}: Total ${tot_int} ({len(items)} ítems).",
                    "presupuestos"
                )
                append_memory(
                    f"Presupuesto {pdf_res['numero']} generado para {client}: Total ${tot_int}.",
                    ""
                )
            except Exception as e:
                logger.warning(f"Error actualizando memoria persistente: {e}")

            reply = (
                f"✅ **Presupuesto generado con éxito** (Presupuesto generado correctamente):\n\n"
                f"• **N°:** {pdf_res['numero']}\n"
                f"• **Cliente:** {client}\n"
                f"• **Total:** ${tot_int}\n\n"
                f"📄 Podés descargarlo aquí: [{pdf_res['filename']}]({pdf_res['download_url']}) "
                f"o consultarlo en la pestaña de **Presupuestos**."
            )
            meta["presupuesto_created"] = True
            meta["presupuesto"] = pdf_res
            return reply, None, meta

        # 12.2. Modificar cantidad / Quitar / Consulta de total
        is_mod, mod_prod_id, new_qty = is_modify_quantity_intent(work_message)
        if is_mod and mod_prod_id and new_qty:
            items = draft.get("items", [])
            for it in items:
                if it["id"] == mod_prod_id:
                    it["cantidad"] = new_qty
                    it["subtotal"] = new_qty * it["precio_unitario"]
                    break
            new_tot = int(sum(it["subtotal"] for it in items))
            return f"Actualicé la cantidad a {new_qty} unidad(es). El nuevo total es **${new_tot}**.", draft, meta

        is_rem, rem_prod_id = is_remove_item_intent(work_message)
        if is_rem:
            items = draft.get("items", [])
            if rem_prod_id:
                draft["items"] = [it for it in items if it["id"] != rem_prod_id]
            elif items:
                draft["items"].pop()
            new_tot = int(sum(it["subtotal"] for it in draft["items"]))
            return f"Producto retirado del presupuesto. El nuevo total es **${new_tot}**.", draft, meta

        if is_total_inquiry(work_message):
            items = draft.get("items", [])
            tot = int(sum(it["subtotal"] for it in items))
            client = draft.get("cliente", "")
            lines = [f"El total acumulado del presupuesto{' para **' + client + '**' if client else ''} es de **${tot}**."]
            if items:
                lines.append("\nDetalle de insumos:")
                for it in items:
                    lines.append(f"• {int(it['cantidad'])} unidad(es) de {it['display']} a ${int(it['precio_unitario'])} c/u: ${int(it['subtotal'])}")
            if client:
                lines.append("\n¿Confirmás el presupuesto para emitir el PDF oficial o deseás agregar algún otro insumo?")
            else:
                lines.append("\n¿A nombre de qué cliente o profesional lo preparo?")
            return "\n".join(lines), draft, meta

        # 12.3. Consulta de precio mientras hay borrador ("¿Cuánto sale una caja de jeringas?")
        if is_price_inquiry(work_message):
            reply = handle_price_inquiry_query(work_message, draft=draft)
            return reply, draft, meta

        # 12.4. Incorporación dinámica de insumos y/o cliente en el borrador en curso
        new_items = parse_presupuesto_items(work_message)
        is_add_more, add_prod_id, add_qty = is_add_more_intent(work_message)
        cand_client = extract_client_name(work_message)
        if not cand_client and (draft.get("awaiting_client") or not draft.get("cliente")):
            is_v, c_name = is_valid_person_or_client_name(work_message)
            if is_v:
                cand_client = c_name

        items_changed = False
        client_assigned = False

        if cand_client and (not draft.get("cliente") or draft.get("awaiting_client") or "para " in work_message.lower() or "cambia" in work_message.lower()):
            draft["cliente"] = cand_client
            draft["awaiting_client"] = False
            client_assigned = True

        current_items = draft.get("items", [])
        if new_items:
            for it in new_items:
                existing = next((x for x in current_items if x["id"] == it["id"]), None)
                if existing:
                    existing["cantidad"] += it["cantidad"]
                    existing["subtotal"] = existing["cantidad"] * existing["precio_unitario"]
                else:
                    current_items.append(it)
            draft["items"] = current_items
            items_changed = True
        elif is_add_more and add_qty > 0:
            target = None
            if add_prod_id:
                target = next((x for x in current_items if x["id"] == add_prod_id), None)
            elif current_items:
                target = current_items[-1]
            if target:
                target["cantidad"] += add_qty
                target["subtotal"] = target["cantidad"] * target["precio_unitario"]
                draft["items"] = current_items
                items_changed = True

        if items_changed or client_assigned:
            current_items = draft.get("items", [])
            client = draft.get("cliente", "")
            if current_items:
                tot = int(sum(it["subtotal"] for it in current_items))
                if is_add_more and add_qty > 0 and target:
                    target_disp = target["display"] if target else "insumo"
                    new_q = int(target["cantidad"])
                    pu = int(target["precio_unitario"])
                    sub = int(target["subtotal"])
                    lines = [f"Perfecto, sumé {add_qty} caja(s) más de **{target_disp.split('(')[0].strip()}**." if "Caja" in target_disp else f"Perfecto, sumé {add_qty} unidad(es) más de **{target_disp}**."]
                    lines.append(f"El borrador ahora tiene **{new_q} unidades** a ${pu} cada una, con un subtotal de **${sub}**.")
                    if client:
                        lines.append(f"\nTotal: **${tot}**.\n\n¿Confirmás el presupuesto para emitir el PDF oficial o deseás agregar algún otro insumo?")
                    else:
                        draft["awaiting_client"] = True
                        lines.append(f"\nTotal acumulado: **${tot}**.\n\n¿A nombre de qué cliente o profesional lo preparo?")
                    return " ".join(lines[:2]) + ("\n\n" + "\n".join(lines[2:]) if len(lines) > 2 else ""), draft, meta

                if client:
                    if client_assigned or len(new_items or []) > 1:
                        lines = [f"Excelente. El presupuesto para **{client}** queda así:\n"]
                        for it in current_items:
                            lines.append(f"• {int(it['cantidad'])} unidad(es) de {it['display']} a ${int(it['precio_unitario'])} c/u: ${int(it['subtotal'])}")
                        lines.append(f"\nTotal: **${tot}**.\n\n¿Confirmás el presupuesto? Puedo emitir el PDF oficial en este momento.")
                        return "\n".join(lines), draft, meta
                    else:
                        lines = []
                        if new_items and len(new_items) == 1:
                            it = new_items[0]
                            q = int(it["cantidad"])
                            pu = int(it["precio_unitario"])
                            sub = int(it["subtotal"])
                            disp = it["display"]
                            desc = f"{q} caja(s) de {disp.split('(')[0].strip()}" if "Caja" in disp else f"{q} unidad(es) de {disp}"
                            lines.append(f"Agregué {desc} al presupuesto para **{client}**, a ${pu} c/u con un subtotal de **${sub}**.")
                        else:
                            lines.append(f"Agregué los insumos solicitados al presupuesto para **{client}**.")
                        lines.append(f"\nNuevo total: **${tot}**.\n\n¿Confirmás el presupuesto? Puedo emitir el PDF oficial en este momento.")
                        return "\n".join(lines), draft, meta
                else:
                    draft["awaiting_client"] = True
                    lines = ["Inicié el borrador con los insumos solicitados:\n"]
                    for it in current_items:
                        lines.append(f"• {int(it['cantidad'])} unidad(es) de {it['display']} a ${int(it['precio_unitario'])} c/u: ${int(it['subtotal'])}")
                    lines.append(f"\nTotal: **${tot}** (Stock ILIMITADO).\n\n¿A nombre de qué cliente o profesional lo preparo?")
                    return "\n".join(lines), draft, meta
            else:
                return (
                    f"Perfecto, el presupuesto quedó asignado a **{client}**. "
                    f"¿Qué productos o insumos médicos y qué cantidades querés incluir? (Por ejemplo: *'2 cajas de guantes y 3 cajas de jeringas'*).",
                    draft,
                    meta
                )

    # 13. Consulta de precios fuera de presupuesto
    if is_price_inquiry(work_message):
        return handle_price_inquiry_query(work_message, draft=draft), draft, meta

    # 14. Inicio de presupuesto explícito o pedido directo de productos
    # Ejemplos: "Hola, quiero un presupuesto para 4 cajas de guantes"
    #          "Quiero cuatro cajas de guantes"
    #          "Necesito preparar un presupuesto para un consultorio"
    #          "Necesito cotizar materiales para un cliente"
    if is_budget_initiation_intent(work_message) or is_direct_product_demand(work_message):
        parsed_items = parse_presupuesto_items(work_message)
        extracted_client = extract_client_name(work_message)
        if not extracted_client:
            is_valid, cand_name = is_valid_person_or_client_name(work_message)
            if is_valid and not parsed_items:
                extracted_client = cand_name

        new_draft = {
            "active": True,
            "cliente": extracted_client or "",
            "items": parsed_items,
            "awaiting_client": not bool(extracted_client),
            "paused": False,
        }

        greeting_intro = "¡Hola! Claro, preparemos el presupuesto. " if has_greeting_prefix else ""

        # Caso 14.1: Productos y cantidades indicados
        if parsed_items:
            tot = int(sum(it["subtotal"] for it in parsed_items))
            if len(parsed_items) == 1:
                it = parsed_items[0]
                q = int(it["cantidad"])
                pu = int(it["precio_unitario"])
                sub = int(it["subtotal"])
                disp = it["display"]
                desc_str = f"{q} caja(s) de {disp.split('(')[0].strip()}" if "Caja" in disp else f"{q} unidad(es) de {disp}"

                if extracted_client:
                    reply = (
                        f"{greeting_intro}Agregué {desc_str} al borrador para **{extracted_client}**, "
                        f"a ${pu} cada una, con un total de **${sub}**. "
                        f"¿Confirmás el presupuesto para emitir el PDF oficial?"
                    )
                else:
                    reply = (
                        f"{greeting_intro}Agregué {desc_str} al borrador, "
                        f"a ${pu} cada una, con un subtotal de **${sub}**. "
                        f"¿A nombre de qué cliente o profesional lo preparo?"
                    )
            else:
                lines = [f"{greeting_intro}Inicié el borrador con los insumos solicitados:\n"]
                for it in parsed_items:
                    lines.append(f"• {int(it['cantidad'])} unidad(es) de {it['display']} a ${int(it['precio_unitario'])} c/u: ${int(it['subtotal'])}")
                lines.append(f"\nTotal: **${tot}** (Stock ILIMITADO).")
                if extracted_client:
                    lines.append(f"\n¿Confirmás el presupuesto para **{extracted_client}**?")
                else:
                    lines.append("\n¿A nombre de qué cliente o profesional lo preparo?")
                reply = "\n".join(lines)

            return reply, new_draft, meta

        # Caso 14.2: Solo cliente o institución indicada
        if extracted_client:
            reply = (
                f"{greeting_intro}¡Con gusto! He iniciado un borrador de presupuesto para **{extracted_client}**.\n\n"
                f"¿Qué insumos médicos y qué cantidades necesitás incluir? (Por ejemplo: *'2 cajas de guantes y 3 cajas de jeringas'*)."
            )
            return reply, new_draft, meta

        # Caso 14.3: Solo petición general de presupuesto
        return (
            f"{greeting_intro}¡Con gusto! Para armar el presupuesto oficial, indicame el nombre y apellido del profesional o cliente y los insumos que necesitás cotizar.",
            new_draft,
            meta
        )

    # 15. Consultas institucionales y de asistencia inteligente (Turnos, Médicos, Especialidades, Identidad)
    norm = normalize_text(work_message)

    # 15.1. Identidad y alcance
    if any(w in norm for w in ["quien sos", "como te llamas", "que sos", "tu nombre", "para que servis"]):
        return (
            "Soy el **Asistente Inteligente del Panel Administrativo de UMSA Centro Médico**. "
            "Mi función es ayudarte a coordinar la gestión administrativa interna: emitir cotizaciones y presupuestos oficiales en PDF "
            "(a partir de nuestro catálogo de insumos con stock permanente y precios regulados), orientarte sobre los medios de pago y cobranzas, "
            "consultar turnos médicos registrados y administrar el almacenamiento local en `files_storage/`. ¿En qué puedo colaborar hoy?",
            draft,
            meta
        )

    # 15.2. Turnos y Citas
    if any(w in norm for w in ["turno", "turnos", "agenda", "citas", "sacar turno", "pedir turno", "agendar"]):
        return (
            "En UMSA Centro Médico, la gestión y asignación de turnos opera a través del endpoint central `/crear-turno/` conectado "
            "con el sistema central. En este panel podés consultar los registros, notas y agendas en el módulo `files_storage/turnos/`. "
            "Por razones de confidencialidad institucional, la disponibilidad de turnos y datos de pacientes no deben ser inventados "
            "y deben verificarse en la base de datos oficial.",
            draft,
            meta
        )

    # 15.3. Profesionales y Especialidades
    if any(w in norm for w in ["profesional", "profesionales", "medico", "medicos", "doctor", "doctores", "especialidad", "especialidades", "pediatria", "cardiologia", "traumatologia"]):
        return (
            "UMSA Centro Médico cuenta con profesionales en especialidades como Clínica Médica, Pediatría, Cardiología, Traumatología, "
            "Ginecología y Cirugía Menor. Las nóminas y registros se gestionan de forma privada en los módulos `files_storage/profesionales/` "
            "y `files_storage/especialidades/`. Si necesitás preparar una cotización de insumos descartables para alguno de los consultorios, decime para quién y qué insumos precisa.",
            draft,
            meta
        )

    # 15.4. Ubicación y Horarios
    if any(w in norm for w in ["donde queda", "donde estan", "direccion", "ubicacion", "horario", "horarios", "a que hora abren"]):
        return (
            "UMSA Centro Médico está ubicado en San Andrés de Giles. Nuestro horario de atención administrativa y consultorios "
            "es de **lunes a viernes de 08:00 a 20:00 hs** y **sábados de 08:00 a 13:00 hs**.",
            draft,
            meta
        )

    # 15.5. Medios de pago específicos
    if "transferencia" in norm:
        return (
            "Aceptamos **Transferencia Bancaria** institucional. Los datos bancarios (Banco, Titular, CBU, Alias) se encuentran "
            "configurados en el módulo de Cobranzas. Una vez recibido el comprobante, se registra en el panel vinculándolo al presupuesto oficial.",
            draft,
            meta
        )
    if "mercado pago" in norm or "mercadopago" in norm:
        return (
            "Aceptamos **Mercado Pago** mediante código QR en administración y enlaces de pago oficiales provistos por el centro médico.",
            draft,
            meta
        )
    if "tarjeta" in norm:
        return (
            "Aceptamos pagos con **tarjetas de débito y crédito** (Visa, Mastercard, Cabal) a través de terminales electrónicas POS en ventanilla de administración.",
            draft,
            meta
        )
    if "efectivo" in norm:
        return (
            "Se realizan cobros en **efectivo** en ventanilla de caja de lunes a viernes de 08:00 a 20:00 hs, emitiéndose el comprobante oficial correspondiente.",
            draft,
            meta
        )

    # 16. Fallback conversacional contextual (Lógico, adaptativo, sin repetir fórmulas automáticas)
    if history and len(history) >= 2:
        last_bot = history[-2].get("content", "").lower() if history[-2].get("role") == "assistant" else ""
        if "presupuesto" in last_bot and draft and draft.get("active"):
            return (
                f"Comprendido. Respecto al presupuesto en curso para **{draft.get('cliente') or 'el consultorio'}**, "
                f"¿querés que sumemos algún insumo adicional, modifiquemos cantidades o confirmemos el PDF oficial?",
                draft,
                meta
            )
        if any(p in last_bot for p in ["guantes", "jeringas", "gasa", "algodon", "alcohol", "oxigenada", "barbijos", "cinta", "cofias", "camisolines"]):
            return (
                "Todos los insumos de nuestro catálogo cuentan con disponibilidad inmediata y Stock Ilimitado. "
                "Si querés armar un presupuesto formal con estos productos, solo decime para quién y qué cantidades necesitás.",
                draft,
                meta
            )

    return (
        "Comprendo lo que me planteás. En este momento el servicio externo de conocimiento general no está disponible o la consulta excede el marco del sistema; "
        "sin embargo, como asistente administrativo del Centro Médico UMSA puedo orientarte con precisión sobre insumos descartables con stock permanente, "
        "armar presupuestos en PDF, consultar medios de pago habilitados o gestionar archivos del centro médico. "
        "¿Sobre cuál de estos temas preferís que avancemos?",
        draft,
        meta
    )


def should_handle_locally(message: str, session_state: dict | None) -> bool:
    """
    Determina si el mensaje debe ser resuelto determinísticamente por Django.
    Resuelve localmente todas las intenciones administrativas, de catálogo, precios,
    definiciones sanitarias, presupuestos y medios de pago.
    """
    norm = normalize_text(message)
    if is_greeting(norm) or is_thanks(norm) or is_how_are_you(norm):
        return True
    if is_change_topic(norm) or is_budget_pause(norm):
        return True
    if is_system_help(norm):
        return True
    if is_payment_methods_query(norm):
        return True
    if is_inventory_catalog_query(norm) or handle_inventory_query(norm) is not None:
        return True
    if is_price_inquiry(norm):
        return True
    if is_budget_initiation_intent(norm) or is_direct_product_demand(norm):
        return True
    if is_budget_resume(norm):
        return True
    if is_cancellation(norm):
        return True
    if has_negative_budget_constraint(norm):
        return True
    if handle_uncatalogued_product_inquiry(norm) is not None:
        return True
    if handle_definition_or_medical_inquiry(norm) is not None:
        return True
    if handle_general_knowledge_or_question(norm) is not None:
        return True
    if session_state and session_state.get("active"):
        return True
    return False


def process_local_interaction(
    message: str,
    session_state: dict | None,
    module: str = "",
    history: list | None = None
) -> tuple[str | None, dict | None, dict]:
    """
    Punto de entrada de resolución determinística local:
    - Resuelve localmente con máxima precisión y contexto.
    - Si no corresponde a una intención local, retorna (None, session_state, {}) para delegar a Claude.
    """
    if should_handle_locally(message, session_state):
        return process_conversational_message(message, session_state, module, history)
    return None, session_state, {}
