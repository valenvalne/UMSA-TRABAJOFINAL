import os
import sys
import re
import unicodedata

sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

from app.services import get_inventario, append_memory
from app.presupuestos import generate_presupuesto_pdf
from app.local_assistant import (
    PRODUCT_KEYWORDS,
    PRODUCT_DISPLAY_NAMES,
    PRODUCT_SHORT_NAMES,
    NUMBER_WORDS,
    normalize_text,
    clean_client_name,
    extract_client_name,
    detect_product_id,
    extract_quantity_near_keyword,
    parse_presupuesto_items,
    is_valid_person_or_client_name,
    is_system_help,
    is_payment_methods_query,
    is_inventory_catalog_query,
    is_price_inquiry,
    is_cancellation,
    is_confirmation,
    is_total_inquiry,
    is_hypothetical_remove_intent,
    is_remove_item_intent,
    is_modify_quantity_intent,
    handle_definition_or_medical_inquiry,
    handle_general_knowledge_or_question,
    handle_system_help_query,
    handle_payment_methods_query,
    handle_inventory_query,
    handle_price_inquiry_query,
)

def strip_greeting_prefix(text: str) -> tuple[bool, str]:
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


def has_negative_budget_constraint(text: str) -> bool:
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


def is_add_more_intent(text: str) -> tuple[bool, int | None, int]:
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


def is_budget_pause(text: str) -> bool:
    norm = normalize_text(text).strip()
    triggers = [
        "deja el presupuesto en pausa", "dejar en pausa", "en pausa", "pausa el presupuesto",
        "pausar el presupuesto", "dejemos en pausa", "dejalo en pausa", "pone en pausa",
        "dejemos el presupuesto para despues", "dejemos el presupuesto", "despues vemos el presupuesto",
        "luego seguimos con el presupuesto", "dejemos esto para despues"
    ]
    return any(t in norm for t in triggers)


def is_budget_resume(text: str) -> bool:
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


def is_budget_initiation_intent(text: str) -> bool:
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


def handle_uncatalogued_product_inquiry(text: str, inventario=None) -> str | None:
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


def dispatch_conversational_turn(message: str, session_draft: dict | None) -> tuple[str, dict | None, dict]:
    meta = {}
    draft = session_draft.copy() if session_draft else None
    has_active_draft = draft is not None and draft.get("active", False)

    # 1. Analizar si hay saludo al inicio
    has_greeting_prefix, remainder = strip_greeting_prefix(message)
    work_message = remainder if remainder else message
    norm_rem = normalize_text(remainder).strip()
    
    # Si es solo un saludo sin contenido adicional ("Hola", "Buenas", "Hola ¿cómo estás?")
    if has_greeting_prefix and (not remainder or is_valid_person_or_client_name(remainder)[0] is False and norm_rem in ["como estas", "que tal", "como te va", "todo bien", ""]):
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
            return "Presupuesto cancelado. Podés solicitar uno nuevo en cualquier momento o consultarme sobre insumos y medios de pago.", None, meta
        return "Operación cancelada. ¿En qué más puedo ayudarte?", None, meta

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

    # 4. Retomar presupuesto
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

    # 10. Catálogo general de insumos disponibles
    if is_inventory_catalog_query(work_message):
        reply = handle_inventory_query(work_message)
        if reply:
            return reply, draft, meta

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
            reply = (
                f"✅ **Presupuesto generado correctamente**\n\n"
                f"• **N°:** {pdf_res['numero']}\n"
                f"• **Cliente:** {client}\n"
                f"• **Total:** ${tot_int}\n\n"
                f"📄 Podés descargarlo aquí: [{pdf_res['filename']}]({pdf_res['download_url']}) "
                f"o consultarlo en la pestaña de **Presupuestos**."
            )
            meta["presupuesto_created"] = True
            meta["presupuesto"] = pdf_res
            return reply, None, meta

        # 12.1. Sumar unidades relativas ("Necesito otras dos cajas más", "Agregá 2 más")
        is_add_more, add_prod_id, add_qty = is_add_more_intent(work_message)
        if is_add_more and add_qty > 0:
            items = draft.get("items", [])
            target = None
            if add_prod_id:
                target = next((it for it in items if it["id"] == add_prod_id), None)
            elif items:
                target = items[-1]

            if target:
                target["cantidad"] += add_qty
                target["subtotal"] = target["cantidad"] * target["precio_unitario"]
                new_total = int(sum(it["subtotal"] for it in items))
                client = draft.get("cliente")
                disp = target["display"]
                new_q = int(target["cantidad"])
                pu = int(target["precio_unitario"])
                sub = int(target["subtotal"])

                lines = [f"Perfecto, sumé {add_qty} caja(s) más de **{disp.split('(')[0].strip()}**." if "Caja" in disp else f"Perfecto, sumé {add_qty} unidad(es) más de **{disp}**."]
                lines.append(f"El borrador ahora tiene **{new_q} unidades** a ${pu} cada una, con un subtotal de **${sub}**.")
                if not client:
                    draft["awaiting_client"] = True
                    lines.append(f"\nTotal acumulado: **${new_total}**.")
                    lines.append("¿A nombre de qué cliente o profesional lo preparo?")
                else:
                    lines.append(f"\nTotal: **${new_total}**.")
                    lines.append("¿Confirmás el presupuesto para emitir el PDF oficial o deseás agregar algún otro insumo?")
                return " ".join(lines[:2]) + ("\n\n" + "\n".join(lines[2:]) if len(lines) > 2 else ""), draft, meta

        # 12.2. Esperando cliente (solo si no es otra instrucción operativa)
        if draft.get("awaiting_client"):
            is_valid_name, cand_name = is_valid_person_or_client_name(work_message)
            if is_valid_name:
                draft["cliente"] = cand_name
                draft["awaiting_client"] = False
                items = draft.get("items", [])
                if items:
                    tot_int = int(sum(it["subtotal"] for it in items))
                    lines = [f"Excelente. El presupuesto para **{cand_name}** queda así:\n"]
                    for it in items:
                        lines.append(f"• {int(it['cantidad'])} unidad(es) de {it['display']} a ${int(it['precio_unitario'])} c/u: ${int(it['subtotal'])}")
                    lines.append(f"\nTotal: **${tot_int}**.\n\n¿Confirmás el presupuesto para emitir el PDF oficial?")
                    return "\n".join(lines), draft, meta
                else:
                    return f"Perfecto, el presupuesto quedó asignado a **{cand_name}**. ¿Qué insumos médicos y qué cantidades querés incluir?", draft, meta

        # 12.4. Consulta de precio mientras hay borrador ("¿Cuánto sale una caja de jeringas?")
        if is_price_inquiry(work_message):
            reply = handle_price_inquiry_query(work_message, draft=draft)
            return reply, draft, meta

        # 12.5. Modificar cantidad / Quitar / Consulta de total
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
            return f"El total acumulado del presupuesto es de **${tot}**.", draft, meta

    # 13. Consulta de precios fuera de presupuesto
    if is_price_inquiry(work_message):
        return handle_price_inquiry_query(work_message, draft=draft), draft, meta

    # 14. Inicio de presupuesto explícito o pedido directo de productos
    # Ejemplos: "Hola, quiero un presupuesto para 4 cajas de guantes"
    #          "Quiero cuatro cajas de guantes"
    #          "Necesito preparar un presupuesto para un consultorio"
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
            f"{greeting_intro}¡Con gusto! Para armar el presupuesto oficial, indicame los insumos médicos que necesitás y el nombre del profesional o institución.",
            new_draft,
            meta
        )

    # 15. Fallback general
    return (
        "Como asistente administrativo de UMSA Centro Médico, puedo ayudarte a consultar insumos y precios oficiales, "
        "preparar cotizaciones o presupuestos formales en PDF, orientarte sobre los medios de pago aceptados, "
        "o consultar archivos de administración y turnos. ¿Sobre qué tema te gustaría consultar?",
        draft,
        meta
    )


print("Dispatcher defined. Running automated tests on cases A through H...")

# Test A
rA, sA, _ = dispatch_conversational_turn("Hola, quiero un presupuesto para 4 cajas de guantes", None)
print("\n--- TEST A: 'Hola, quiero un presupuesto para 4 cajas de guantes' ---")
print("R:", rA)
print("S:", sA)
assert "10000" in rA or "10.000" in rA
assert "cliente o profesional" in rA.lower()
assert sA["active"] is True and len(sA["items"]) == 1 and sA["items"][0]["cantidad"] == 4

# Test B
rB, sB, _ = dispatch_conversational_turn("Necesito otras dos cajas más", sA)
print("\n--- TEST B: 'Necesito otras dos cajas más' ---")
print("R:", rB)
print("S:", sB)
assert "15000" in rB or "15.000" in rB
assert sB["items"][0]["cantidad"] == 6

# Test C
rC, sC, _ = dispatch_conversational_turn("¿Cuánto sale una caja de jeringas?", sB)
print("\n--- TEST C: '¿Cuánto sale una caja de jeringas?' ---")
print("R:", rC)
print("S:", sC)
assert "3500" in rC
assert sC["items"][0]["cantidad"] == 6  # Does not add automatically!
assert len(sC["items"]) == 1

# Test D
rD, sD, _ = dispatch_conversational_turn("Dejá el presupuesto en pausa. ¿Qué medios de pago aceptan?", sC)
print("\n--- TEST D: 'Dejá el presupuesto en pausa. ¿Qué medios de pago aceptan?' ---")
print("R:", rD)
print("S:", sD)
assert "Efectivo" in rD and "Mercado Pago" in rD
assert sD["paused"] is True

# Test E
rE, sE, _ = dispatch_conversational_turn("Volvamos al presupuesto de antes", sD)
print("\n--- TEST E: 'Volvamos al presupuesto de antes' ---")
print("R:", rE)
print("S:", sE)
assert sE["paused"] is False
assert "15000" in rE or "15.000" in rE
assert sE["items"][0]["cantidad"] == 6

# Test F
rF, sF, _ = dispatch_conversational_turn("Quiero cuatro cajas de guantes", None)
print("\n--- TEST F: 'Quiero cuatro cajas de guantes' ---")
print("R:", rF)
print("S:", sF)
assert "10000" in rF or "10.000" in rF
assert sF["items"][0]["cantidad"] == 4

# Test G
rG, sG, _ = dispatch_conversational_turn("Quiero saber cuánto cuestan cuatro cajas de guantes, pero todavía no hagas un presupuesto", None)
print("\n--- TEST G: 'Quiero saber cuánto cuestan cuatro cajas de guantes, pero todavía no hagas un presupuesto' ---")
print("R:", rG)
print("S:", sG)
assert "10000" in rG or "10.000" in rG
assert sG is None  # MUST NOT CREATE BUDGET DRAFT

# Test H
rH, sH, _ = dispatch_conversational_turn("¿Cuánto cuesta un tensiómetro digital?", None)
print("\n--- TEST H: '¿Cuánto cuesta un tensiómetro digital?' ---")
print("R:", rH)
print("S:", sH)
assert "no se encuentra disponible" in rH or "no forma parte de nuestro catálogo" in rH

print("\n\n>>> ALL 8 TEST CASES PASSED WITH 100% SUCCESS! <<<")

print("\n--- NOW TESTING THE 10 PRIOR MANDATORY QUERIES ---")
# 1. "Hola"
r1, s1, _ = dispatch_conversational_turn("Hola", None)
assert "bienvenida" in r1.lower()
print("[OK] 1. 'Hola'")

# 2. "¿Qué podés hacer?"
r2, s2, _ = dispatch_conversational_turn("¿Qué podés hacer?", None)
assert "panel administrativo" in r2.lower()
print("[OK] 2. '¿Qué podés hacer?'")

# 3. "¿Cuánto cuestan los guantes de látex?"
r3, s3, _ = dispatch_conversational_turn("¿Cuánto cuestan los guantes de látex?", None)
assert "2500" in r3 and s3 is None
print("[OK] 3. '¿Cuánto cuestan los guantes de látex?'")

# 4. "¿Qué productos tienen disponibles?"
r4, s4, _ = dispatch_conversational_turn("¿Qué productos tienen disponibles?", None)
assert "catálogo" in r4.lower() or "catalogo" in r4.lower()
print("[OK] 4. '¿Qué productos tienen disponibles?'")

# 5. "¿Qué medios de pago aceptan?"
r5, s5, _ = dispatch_conversational_turn("¿Qué medios de pago aceptan?", None)
assert "efectivo" in r5.lower() and "mercado pago" in r5.lower()
print("[OK] 5. '¿Qué medios de pago aceptan?'")

# 6. "Necesito preparar un presupuesto para un consultorio"
r6, s6, _ = dispatch_conversational_turn("Necesito preparar un presupuesto para un consultorio", None)
assert "consultorio" in r6.lower() and s6["active"] is True
print("[OK] 6. 'Necesito preparar un presupuesto para un consultorio'")

# 7. "¿Y cuánto cuesta la caja de jeringas?"
r7, s7, _ = dispatch_conversational_turn("¿Y cuánto cuesta la caja de jeringas?", s6)
assert "3500" in r7
print("[OK] 7. '¿Y cuánto cuesta la caja de jeringas?'")

# 8. "Dejemos el presupuesto para después. ¿Qué es una gasa?"
r8, s8, _ = dispatch_conversational_turn("Dejemos el presupuesto para después. ¿Qué es una gasa?", s7)
assert "gasa médica" in r8.lower() and s8["paused"] is True
print("[OK] 8. 'Dejemos el presupuesto para después. ¿Qué es una gasa?'")

# 9. "Volvamos al presupuesto anterior"
r9, s9, _ = dispatch_conversational_turn("Volvamos al presupuesto anterior", s8)
assert "consultorio" in r9.lower() and s9["paused"] is False
print("[OK] 9. 'Volvamos al presupuesto anterior'")

# 10. "¿Cuál es la capital de Francia?"
r10, s10, _ = dispatch_conversational_turn("¿Cuál es la capital de Francia?", s9)
assert "parís" in r10.lower() or "paris" in r10.lower()
print("[OK] 10. '¿Cuál es la capital de Francia?'")

print("\n>>> ALL 18 TESTS (8 NEW + 10 PRIOR) PASSED CONCURRENTLY WITH 100% SUCCESS! <<<")
