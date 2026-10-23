import json
import os
import re
import logging
from pathlib import Path
from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from anthropic import Anthropic

logger = logging.getLogger(__name__)

from .services import (
    STORAGE,
    ensure_module,
    list_files,
    list_files_detailed,
    list_modules,
    load_history,
    save_history,
    clear_history,
    read_file,
    write_file,
    delete_file,
    append_memory,
    get_memory_content,
    create_subfolder,
    system_prompt,
    tools,
    execute_tool,
    safe_name,
    update_index,
    get_modules_summary,
    get_system_status,
    get_inventario,
    update_or_create_inventario_item,
)
from .presupuestos import (
    generate_presupuesto_pdf,
    get_presupuestos_historial,
    get_presupuesto_by_numero,
    get_dashboard_metrics,
    search_global,
)
from .umsa import status, create_turno_note
from .local_assistant import process_local_interaction, process_conversational_message, parse_presupuesto_items
from .pagos import (
    get_medios_pago,
    get_medio_pago_by_codigo,
    update_medio_pago,
    toggle_medio_pago,
    registrar_pago,
    cancelar_pago,
    get_pagos_historial,
    get_pagos_dashboard_metrics,
    get_presupuesto_pagos_summary,
    process_mercadopago_webhook,
)
from .ai_engine import get_available_ai_provider, query_llm_intelligence

def index(request):
    """
    Vista principal del Panel Administrativo UMSA IA.
    Carga el estado del sistema, archivos y módulos sin exponer secretos.
    """
    ensure_module("")
    ai_status = get_available_ai_provider()
    active_prov = ai_status.get("active")
    claude_connected = bool(active_prov is not None)
    claude_model = active_prov["model"] if active_prov else "Motor Local UMSA IA"
    ai_provider_name = active_prov["name"] if active_prov else "Motor Local UMSA IA"
    
    # Índice maestro
    try:
        index_content = read_file("INDEX.md", "")
    except Exception:
        index_content = "# Índice no disponible"

    return render(request, "index.html", {
        "files": list_files_detailed(""),
        "modules": list_modules(),
        "modules_summary": get_modules_summary(),
        "system_status": get_system_status(),
        "dashboard_metrics": get_dashboard_metrics(),
        "presupuestos_historial": get_presupuestos_historial(),
        "inventario": get_inventario(),
        "medios_pago": get_medios_pago(),
        "pagos_historial": get_pagos_historial(),
        "pagos_metrics": get_pagos_dashboard_metrics(),
        "umsa": status(),
        "integration": create_turno_note(),
        "memory": get_memory_content(""),
        "index_content": index_content,
        "claude_connected": claude_connected,
        "claude_model": claude_model,
        "ai_provider_name": ai_provider_name,
    })

@require_GET
def files_api(request):
    """
    Lista archivos del almacenamiento con filtros opcionales por módulo.
    """
    module = request.GET.get("module", "").strip()
    try:
        files = list_files_detailed(module)
        modules = list_modules()
        return JsonResponse({"ok": True, "files": files, "modules": modules, "module": module})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

@require_GET
def read_file_api(request):
    """
    Lee el contenido en texto plano de un archivo en files_storage/.
    """
    path = request.GET.get("path", "").strip()
    if not path:
        return JsonResponse({"error": "Debe especificar una ruta de archivo."}, status=400)
    try:
        content = read_file(path)
        return JsonResponse({"ok": True, "path": path, "content": content})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=404)

@require_POST
def save_file_api(request):
    """
    Crea o edita físicamente un archivo en files_storage/ y actualiza el índice.
    """
    try:
        data = json.loads(request.body or "{}")
        filename = (data.get("filename") or "").strip()
        content = data.get("content", "")
        module = (data.get("module") or "").strip()
        if not filename:
            return JsonResponse({"error": "Debe especificar el nombre del archivo."}, status=400)
        saved_rel = write_file(filename, content, module)
        return JsonResponse({
            "ok": True,
            "message": f"Archivo guardado exitosamente: {saved_rel}",
            "rel_path": saved_rel,
            "files": list_files_detailed(module),
        })
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

@require_POST
def delete_file_api(request):
    """
    Elimina físicamente un archivo de files_storage/ y actualiza el índice.
    """
    try:
        data = json.loads(request.body or "{}")
        filename = (data.get("filename") or "").strip()
        module = (data.get("module") or "").strip()
        if not filename:
            return JsonResponse({"error": "Nombre de archivo no especificado."}, status=400)
        msg = delete_file(filename, module)
        return JsonResponse({
            "ok": True,
            "message": msg,
            "files": list_files_detailed(module)
        })
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

@require_GET
def download_file_api(request):
    """
    Permite descargar cualquier archivo generado en files_storage/ (por ejemplo PDFs).
    """
    rel_path = request.GET.get("path", "").strip()
    if not rel_path:
        raise Http404("Archivo no especificado.")

    try:
        safe_rel = safe_name(rel_path)
        file_path = STORAGE / safe_rel
        if not file_path.exists() or not file_path.is_file():
            raise Http404("El archivo solicitado no existe.")

        content_type = "application/octet-stream"
        if file_path.suffix.lower() == ".pdf":
            content_type = "application/pdf"
        elif file_path.suffix.lower() in [".txt", ".md"]:
            content_type = "text/plain; charset=utf-8"
        elif file_path.suffix.lower() == ".json":
            content_type = "application/json"

        response = FileResponse(open(file_path, "rb"), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{file_path.name}"'
        return response
    except Exception as exc:
        raise Http404(f"Error accediendo al archivo: {exc}")

@require_POST
def create_folder_api(request):
    """
    Crea un módulo aislado en files_storage/ con su estructura base.
    """
    try:
        data = json.loads(request.body or "{}")
        name = create_subfolder(data["folder_name"], data.get("description", ""))
        return JsonResponse({
            "ok": True,
            "folder": name,
            "modules": list_modules(),
            "files": list_files_detailed(name)
        })
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

@require_GET
def memory_api(request):
    """
    Consulta el contenido de MEMORY.md del módulo o global.
    """
    module = request.GET.get("module", "").strip()
    try:
        content = get_memory_content(module)
        return JsonResponse({"ok": True, "memory": content, "module": module})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

@require_POST
def add_memory_api(request):
    """
    Agrega una regla permanente a MEMORY.md.
    """
    try:
        data = json.loads(request.body or "{}")
        note = (data.get("note") or "").strip()
        module = (data.get("module") or "").strip()
        if not note:
            return JsonResponse({"error": "La regla o nota no puede estar vacía."}, status=400)
        append_memory(note, module)
        return JsonResponse({
            "ok": True,
            "message": "Regla permanente guardada en MEMORY.md.",
            "memory": get_memory_content(module)
        })
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

@require_GET
def history_api(request):
    """
    Consulta el historial de mensajes de CHAT_HISTORY.json.
    """
    module = request.GET.get("module", "").strip()
    try:
        return JsonResponse({"ok": True, "history": load_history(module), "module": module})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

@require_POST
def clear_history_api(request):
    """
    Limpia el historial de conversación del módulo seleccionado.
    """
    try:
        data = json.loads(request.body or "{}")
        module = (data.get("module") or "").strip()
        clear_history(module)
        return JsonResponse({"ok": True, "message": "Historial limpiado."})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

@require_POST
def generate_presupuesto_api(request):
    """
    Endpoint directo para generar un presupuesto en PDF con cálculos matemáticos
    y guardado físico en files_storage/presupuestos/.
    """
    try:
        data = json.loads(request.body or "{}")
        cliente = (data.get("cliente") or "").strip()
        if not cliente:
            return JsonResponse({"error": "Debe especificar el nombre del profesional o cliente."}, status=400)

        productos = data.get("productos", [])
        if not productos:
            return JsonResponse({"error": "Debe agregar al menos un producto o ítem."}, status=400)

        # Validar precios unitarios
        for p in productos:
            pu = p.get("precio_unitario")
            if pu is None or pu == "" or float(pu) < 0:
                return JsonResponse({
                    "error": f"El producto '{p.get('descripcion', 'ítem')}' no tiene un precio unitario válido. La IA y el panel no inventan precios."
                }, status=400)

        institucion = (data.get("institucion") or "").strip()
        observaciones = (data.get("observaciones") or "").strip()
        validez = (data.get("validez") or "15 días corridos").strip()
        iva_porcentaje = float(data.get("iva_porcentaje", 21.0))

        res = generate_presupuesto_pdf(
            cliente=cliente,
            productos=productos,
            institucion=institucion,
            observaciones=observaciones,
            validez=validez,
            iva_porcentaje=iva_porcentaje,
        )

        return JsonResponse({
            "ok": True,
            "presupuesto": res,
            "files": list_files_detailed("presupuestos")
        })
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

@require_POST
def ai_parse_presupuesto_api(request):
    """
    Interpreta una solicitud administrativa de presupuesto.
    Arquitectura híbrida: intenta con Claude si está disponible,
    o utiliza el parser local determinístico si no hay créditos o falla la API.
    NUNCA inventa precios ni falla con errores técnicos.
    """
    try:
        data = json.loads(request.body or "{}")
        solicitud = (data.get("solicitud") or "").strip()
        if not solicitud:
            return JsonResponse({"error": "Ingrese el texto de la solicitud."}, status=400)

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if api_key and api_key.startswith("sk-ant-"):
            try:
                prompt_interpretacion = (
                    "Eres el asistente administrativo de UMSA. Interpreta la siguiente solicitud de presupuesto "
                    "enviada por o para un profesional/médico o cliente profesional.\n\n"
                    f"Solicitud: \"{solicitud}\"\n\n"
                    "INVENTARIO OFICIAL CON STOCK ILIMITADO Y PRECIOS FIJOS:\n"
                    "1. Guantes látex descartables (caja x 100 U): $2500 (STOCK ILIMITADO)\n"
                    "2. Jeringas descartables (caja x 50 U): $3500 (STOCK ILIMITADO)\n"
                    "3. Rollo de gasa (90 cm x 100 m): $1200 (STOCK ILIMITADO)\n"
                    "4. Paquete algodón (200 g): $1000 (STOCK ILIMITADO)\n"
                    "5. Alcohol antiséptico (100 ml): $3000 (STOCK ILIMITADO)\n"
                    "6. Agua oxigenada (100 ml): $3000 (STOCK ILIMITADO)\n\n"
                    "INSTRUCCIONES ESTRICTAS:\n"
                    "1. Extrae: cliente, institucion (si existe), validez (si existe o default '15 días corridos'), observaciones (si hay).\n"
                    "2. Extrae la lista de productos: descripcion, cantidad, precio_unitario.\n"
                    "3. REGLA DE PRECIOS: Si el producto coincide con alguno del inventario oficial y no tiene precio explícito, utiliza su precio oficial ($2500, $3500, $1200, $1000, $3000). Si es un producto fuera del inventario oficial y NO figura precio, establece precio_unitario en 0 y missing_prices en true.\n"
                    "4. REGLA DE STOCK: Todos los productos del inventario oficial tienen STOCK ILIMITADO permanente. Cualquier cantidad solicitada es válida.\n"
                    "5. Responde ÚNICAMENTE en formato JSON con la siguiente estructura exacta (sin texto extra):\n"
                    "{\n"
                    '  "cliente": "nombre del profesional o cliente",\n'
                    '  "institucion": "nombre o vacio",\n'
                    '  "validez": "15 días corridos",\n'
                    '  "observaciones": "...",\n'
                    '  "productos": [\n'
                    '    {"descripcion": "...", "cantidad": 20, "precio_unitario": 2500}\n'
                    "  ],\n"
                    '  "missing_prices": false,\n'
                    '  "notice": "Mensaje explicativo si falta algún precio unitario o confirmación"\n'
                    "}"
                )

                client = Anthropic(api_key=api_key)
                resp = client.messages.create(
                    model=os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt_interpretacion}],
                )

                raw_text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()

                parsed = json.loads(raw_text)
                return JsonResponse({"ok": True, "data": parsed})
            except Exception as claude_err:
                logger.warning(f"Claude no disponible en ai_parse_presupuesto ({claude_err}), utilizando parser local determinístico.")

        # Fallback local determinístico si Claude falla o no tiene créditos
        items = parse_presupuesto_items(solicitud)
        m_cli = re.search(r"(?:el\s+|la\s+)?(dr\.|dra\.|doctor|doctora|sr\.|sra\.|don|doña)?\s*([a-zA-ZáéíóúÁÉÍÓÚñÑ]+(?:\s+[a-zA-ZáéíóúÁÉÍÓÚñÑ]+)+)", solicitud, re.IGNORECASE)
        cliente = ""
        if m_cli:
            title = m_cli.group(1) or ""
            name = m_cli.group(2) or ""
            cliente = f"{title.strip()} {name.strip()}".strip()
        elif "para " in solicitud.lower():
            m_para = re.search(r"para\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ\s\.]+?)(?:[:,]|\s+(?:por|de|con|\d+)|$)", solicitud, re.IGNORECASE)
            if m_para:
                cliente = m_para.group(1).strip()
        if not cliente:
            cliente = "Cliente Profesional"

        prods = [
            {
                "descripcion": it["producto"],
                "cantidad": it["cantidad"],
                "precio_unitario": it["precio_unitario"],
            }
            for it in items
        ]
        local_parsed = {
            "cliente": cliente,
            "institucion": "Centro Médico UMSA",
            "validez": "15 días corridos",
            "observaciones": "Interpretado mediante asistente administrativo UMSA.",
            "productos": prods,
            "missing_prices": len(prods) == 0,
            "notice": "Interpretado con éxito a partir del inventario oficial." if prods else "No se detectaron productos del inventario oficial.",
        }
        return JsonResponse({"ok": True, "data": local_parsed})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": f"Error interpretando solicitud: {exc}"}, status=400)

@require_GET
def presupuestos_historial_api(request):
    """
    Retorna el historial completo de presupuestos con filtros opcionales.
    """
    try:
        estado = request.GET.get("estado", "")
        search = request.GET.get("search", "")
        fecha = request.GET.get("fecha", "")
        historial = get_presupuestos_historial(filter_estado=estado, search=search, fecha=fecha)
        return JsonResponse({"ok": True, "historial": historial, "presupuestos": historial})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)

@require_GET
def presupuesto_detail_api(request):
    """
    Retorna el detalle completo de un presupuesto por su número.
    """
    numero = request.GET.get("numero", "").strip()
    if not numero:
        return JsonResponse({"ok": False, "error": "Debe especificar el número de presupuesto."}, status=400)
    pres = get_presupuesto_by_numero(numero)
    if not pres:
        return JsonResponse({"ok": False, "error": f"No se encontró el presupuesto {numero}."}, status=404)
    return JsonResponse({"ok": True, "presupuesto": pres})

@require_GET
def dashboard_metrics_api(request):
    """
    Retorna las métricas en tiempo real del Dashboard con datos reales.
    """
    try:
        metrics = get_dashboard_metrics()
        return JsonResponse({"ok": True, "metrics": metrics})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)

@require_GET
def search_api(request):
    """
    Endpoint de Búsqueda Global:
    Busca sobre inventario, presupuestos y consultas en lenguaje natural sin inventar datos.
    """
    query = request.GET.get("q", "").strip()
    try:
        res = search_global(query)
        return JsonResponse(res)
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc), "has_results": False, "message": "Error procesando búsqueda."}, status=500)

@require_GET
def inventario_api(request):
    """
    Retorna el listado oficial de inventario de insumos médicos con stock ILIMITADO.
    """
    try:
        return JsonResponse({"ok": True, "inventario": get_inventario()})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)

@require_POST
def inventario_save_api(request):
    """
    Crea o edita un insumo del inventario, con soporte para subida de imagen,
    vista previa, reemplazo y restablecimiento a marcador predeterminado.
    """
    try:
        data = {}
        image_file = None
        remove_image = False

        if request.content_type and "multipart/form-data" in request.content_type:
            data = request.POST.dict()
            image_file = request.FILES.get("imagen_file")
            remove_image = str(request.POST.get("quitar_imagen", "")).lower() in ["1", "true", "yes"]
        else:
            data = json.loads(request.body or "{}")
            remove_image = bool(data.get("quitar_imagen"))

        updated = update_or_create_inventario_item(data, image_file=image_file, remove_image=remove_image)
        return JsonResponse({"ok": True, "item": updated, "inventario": get_inventario()})
    except Exception as exc:
        logger.error(f"Error guardando insumo: {exc}")
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

@require_GET
def umsa_status_api(request):
    """
    Comprobación en vivo del estado de conexión con UMSA-Django.
    """
    return JsonResponse({"status": status(), "integration": create_turno_note()})

@require_GET
def index_api(request):
    """
    Consulta el contenido de INDEX.md del módulo o global.
    """
    module = request.GET.get("module", "").strip()
    try:
        content = read_file("INDEX.md", module)
        return JsonResponse({"ok": True, "index": content, "module": module})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

@require_POST
def rebuild_index_api(request):
    """
    Fuerza la reconstrucción del índice semántico INDEX.md.
    """
    try:
        data = json.loads(request.body or "{}")
        module = (data.get("module") or "").strip()
        update_index(module)
        content = read_file("INDEX.md", module)
        return JsonResponse({
            "ok": True,
            "message": "Índice INDEX.md actualizado correctamente.",
            "index": content,
            "module": module,
        })
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

@require_GET
def modules_api(request):
    """
    Lista el resumen de todos los módulos aislados de files_storage/.
    """
    try:
        return JsonResponse({"ok": True, "modules": get_modules_summary()})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

@require_GET
def system_status_api(request):
    """
    Retorna el estado del sistema en tiempo real para el Dashboard.
    """
    try:
        return JsonResponse({"ok": True, "status": get_system_status()})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)

@require_POST
def chat_api(request):
    """
    Manejo híbrido de conversación:
    1. Operaciones determinísticas (Inventario y Presupuestos interactivos) se resuelven
       localmente en Django sin llamar obligatoriamente a Claude.
    2. Preguntas generales, conversación libre y Tool Calling se delegan a Claude.
    3. Si Claude falla por falta de créditos o error de API, el usuario recibe una respuesta
       amigable y orientada al sistema sin errores técnicos en pantalla.
    """
    data = json.loads(request.body or "{}")
    message = (data.get("message") or "").strip()
    module = (data.get("module") or "").strip()
    if not message:
        return JsonResponse({"error": "Escribí un mensaje."}, status=400)

    # 1. Resolución determinística local en Django (Presupuesto interactivo o Inventario)
    session_state = request.session.get("presupuesto_state")
    local_reply, new_state, meta = process_local_interaction(message, session_state, module)
    if local_reply is not None:
        request.session["presupuesto_state"] = new_state
        request.session.modified = True

        history = load_history(module)
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": local_reply})
        save_history(history, module)

        return JsonResponse({
            "ok": True,
            "answer": local_reply,
            "tools_executed": [],
            "files": list_files_detailed(module),
            "memory": get_memory_content(module),
            "presupuesto_created": meta.get("presupuesto_created", False),
            "presupuesto": meta.get("presupuesto"),
        })

    # 2. Consultas generales / Razonamiento / Tool Calling con Multi-Proveedor IA
    # Soporta Google Gemini (gratis sin tarjeta), Groq (Llama 3.3 gratis), Anthropic Claude, OpenAI o Ollama
    provider_info = get_available_ai_provider()
    if provider_info["has_ai"]:
        history = load_history(module)
        history.append({"role": "user", "content": message})
        messages = history[-20:]

        try:
            llm_answer, tool_executed_records, used_provider = query_llm_intelligence(
                system_prompt=system_prompt(),
                messages=messages,
                tools_list=tools(),
                execute_tool_cb=execute_tool,
                module=module,
            )
            if llm_answer is not None:
                history.append({"role": "assistant", "content": llm_answer})
                save_history(history, module)

                presupuesto_created = any(t.get("tool") == "create_presupuesto" for t in tool_executed_records)
                return JsonResponse({
                    "ok": True,
                    "answer": llm_answer,
                    "tools_executed": tool_executed_records,
                    "files": list_files_detailed(module),
                    "memory": get_memory_content(module),
                    "provider": used_provider,
                    "presupuesto_created": presupuesto_created,
                })
        except Exception as exc:
            logger.warning(f"Error consultando motor de IA ({exc}). Usando motor conversacional local.")

    # 3. Respaldo conversacional de Django (sin saldo o fuera de línea)
    fallback_reply, new_state, meta = process_conversational_message(message, session_state, module)
    if new_state is not None:
        request.session["presupuesto_state"] = new_state
        request.session.modified = True
    history = load_history(module)
    if not history or history[-1].get("content") != message:
        history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": fallback_reply})
    save_history(history, module)
    return JsonResponse({
        "ok": True,
        "answer": fallback_reply,
        "tools_executed": [],
        "files": list_files_detailed(module),
        "memory": get_memory_content(module),
        "presupuesto_created": meta.get("presupuesto_created", False),
        "presupuesto": meta.get("presupuesto"),
    })


# =========================================================================
# MÓDULO DE MEDIOS DE PAGO Y GESTIÓN DE COBRANZAS
# =========================================================================

@require_GET
def pagos_medios_api(request):
    """
    Retorna la lista de los 4 medios de pago oficiales con su estado y configuraciones.
    """
    try:
        only_active = request.GET.get("only_active", "").lower() in ["1", "true", "yes"]
        medios = get_medios_pago(only_active=only_active)
        return JsonResponse({"ok": True, "medios": medios})
    except Exception as exc:
        logger.error(f"Error listando medios de pago: {exc}")
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@require_POST
def pagos_medios_toggle_api(request):
    """
    Activa o desactiva un medio de pago desde la interfaz sin perder sus datos históricos.
    """
    try:
        data = json.loads(request.body or "{}")
        codigo = str(data.get("codigo", "")).strip()
        activo = data.get("activo")
        updated = toggle_medio_pago(codigo, activo=activo)
        return JsonResponse({"ok": True, "medio": updated, "medios": get_medios_pago()})
    except Exception as exc:
        logger.error(f"Error toggle medio de pago: {exc}")
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@require_POST
def pagos_medios_save_api(request):
    """
    Guarda o actualiza la configuración, instrucciones o datos bancarios de un medio de pago.
    """
    try:
        data = json.loads(request.body or "{}")
        codigo = str(data.get("codigo", "")).strip()
        updated = update_medio_pago(codigo, data)
        return JsonResponse({"ok": True, "medio": updated, "medios": get_medios_pago()})
    except Exception as exc:
        logger.error(f"Error guardando medio de pago: {exc}")
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@require_GET
def pagos_list_api(request):
    """
    Retorna el historial de pagos con filtros completos por búsqueda, medio, estado y fechas.
    """
    try:
        search = request.GET.get("search", "").strip()
        medio = request.GET.get("medio", "").strip()
        estado = request.GET.get("estado", "").strip()
        fecha = request.GET.get("fecha", "").strip()
        order = request.GET.get("order", "-fecha_pago").strip()
        pagos = get_pagos_historial(
            search=search,
            filter_medio=medio,
            filter_estado=estado,
            fecha_rango=fecha,
            order_by=order,
        )
        return JsonResponse({"ok": True, "pagos": pagos, "count": len(pagos)})
    except Exception as exc:
        logger.error(f"Error listando historial de pagos: {exc}")
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@require_POST
def pagos_registrar_api(request):
    """
    Registra un pago manualmente asociado a un presupuesto existente con validaciones completas.
    """
    try:
        data = json.loads(request.body or "{}")
        pago = registrar_pago(data)
        summary = get_presupuesto_pagos_summary(pago["presupuesto_numero"])
        return JsonResponse({
            "ok": True,
            "pago": pago,
            "presupuesto_summary": summary,
            "metrics": get_pagos_dashboard_metrics(),
        })
    except Exception as exc:
        logger.error(f"Error registrando pago: {exc}")
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@require_POST
def pagos_cancelar_api(request):
    """
    Cancela un pago con registro de auditoría, motivo y actualización del presupuesto.
    """
    try:
        data = json.loads(request.body or "{}")
        pago_id = data.get("pago_id")
        motivo = data.get("motivo", "")
        pago = cancelar_pago(pago_id, motivo)
        summary = get_presupuesto_pagos_summary(pago["presupuesto_numero"])
        return JsonResponse({
            "ok": True,
            "pago": pago,
            "presupuesto_summary": summary,
            "metrics": get_pagos_dashboard_metrics(),
        })
    except Exception as exc:
        logger.error(f"Error cancelando pago: {exc}")
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@require_GET
def pagos_presupuesto_summary_api(request):
    """
    Consulta el estado de pago, total abonado y saldo pendiente de un presupuesto oficial.
    """
    try:
        numero = request.GET.get("numero", "").strip()
        summary = get_presupuesto_pagos_summary(numero)
        return JsonResponse({"ok": True, "summary": summary})
    except Exception as exc:
        logger.error(f"Error consultando resumen de pagos de presupuesto: {exc}")
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@require_GET
def pagos_dashboard_api(request):
    """
    Retorna métricas e indicadores en tiempo real de pagos y cobranzas.
    """
    try:
        metrics = get_pagos_dashboard_metrics()
        return JsonResponse({"ok": True, "metrics": metrics})
    except Exception as exc:
        logger.error(f"Error obteniendo dashboard de pagos: {exc}")
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@require_POST
def mercadopago_webhook_api(request):
    """
    Punto de entrada preparado para notificaciones webhook de Mercado Pago.
    Garantiza idempotencia y auditoría en WebhookLog.
    """
    try:
        payload = json.loads(request.body or "{}")
        headers = dict(request.headers)
        res = process_mercadopago_webhook(payload, headers)
        return JsonResponse({"ok": True, "result": res})
    except Exception as exc:
        logger.error(f"Error en webhook Mercado Pago: {exc}")
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


