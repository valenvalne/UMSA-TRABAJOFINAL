from pathlib import Path
import json
import os
import re
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
STORAGE = BASE / "files_storage"
CLAUDE_MD = BASE / "claude.md"

def safe_name(name):
    """
    Valida y normaliza nombres de archivo o rutas relativas
    para evitar directory traversal y accesos fuera de files_storage/.
    """
    name = str(name).strip().replace("\\", "/")
    if not name or name.startswith("/") or ".." in Path(name).parts:
        raise ValueError(f"Nombre de archivo o carpeta no permitido: {name}")
    return name

def module_dir(module=""):
    module = safe_name(module) if module else ""
    path = STORAGE / module
    path.mkdir(parents=True, exist_ok=True)
    return path

def ensure_module(module=""):
    path = module_dir(module)
    for name, content in {
        "INDEX.md": f"# Índice del módulo `{module or 'raíz'}`\n\n| Archivo | Última Modificación | Descripción |\n|---|---|---|\n",
        "MEMORY.md": f"# Memoria Persistente - Módulo `{module or 'Global'}`\n\n## Reglas y Directivas\n\n",
        "CHAT_HISTORY.json": "[]",
    }.items():
        target = path / name
        if not target.exists():
            target.write_text(content, encoding="utf-8")
    return path

def list_modules():
    """
    Lista todos los nombres de submódulos (carpetas de primer nivel) dentro de files_storage.
    """
    STORAGE.mkdir(parents=True, exist_ok=True)
    mods = []
    for d in sorted(STORAGE.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            mods.append(d.name)
    return mods

def describe_file(name):
    """
    Retorna una descripción legible del propósito del archivo según su nombre y extensión.
    """
    if name == "MEMORY.md":
        return "Memoria persistente de reglas y directivas"
    if name == "INDEX.md":
        return "Índice de archivos del módulo"
    if name == "CHAT_HISTORY.json":
        return "Historial persistente de conversación"
    if name.lower().endswith(".pdf"):
        return "Presupuesto oficial emitido (PDF)"
    if name.lower().endswith(".txt"):
        return "Documento de texto plano administrativo"
    if name.lower().endswith(".md"):
        return "Documento Markdown administrativo"
    if name == "inventario.json":
        return "Catálogo e inventario oficial de insumos médicos"
    if name.lower().endswith(".json"):
        return "Estructura de datos JSON"
    return "Archivo gestionado por el sistema"

def update_index(module=""):
    """
    Mantiene y actualiza automáticamente los archivos INDEX.md tanto
    del módulo específico como del índice global maestro en files_storage/INDEX.md.
    """
    STORAGE.mkdir(parents=True, exist_ok=True)

    # 1. Si se especificó un módulo, actualizar su INDEX.md local
    if module:
        mod_path = ensure_module(module)
        mod_index = mod_path / "INDEX.md"
        rows = []
        for p in sorted(mod_path.rglob("*")):
            if p.is_file() and p.name != "INDEX.md":
                rel = str(p.relative_to(mod_path)).replace("\\", "/")
                dt = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                desc = describe_file(p.name)
                rows.append(f"| `{rel}` | {dt} | {desc} |")
        text = (
            f"# Índice del Módulo `{module}`\n\n"
            f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            "| Archivo | Última Modificación | Descripción |\n|---|---|---|\n"
            + ("\n".join(rows) if rows else "| *(vacío)* | - | Sin archivos adicionales |")
            + "\n"
        )
        mod_index.write_text(text, encoding="utf-8")

    # 2. Actualizar el Índice Global Maestro en files_storage/INDEX.md
    root_index = STORAGE / "INDEX.md"
    modules = list_modules()
    mod_rows = []
    module_descriptions = {
        "turnos": "Gestión y agendas de turnos médicos",
        "pacientes": "Información administrativa de pacientes",
        "profesionales": "Nómina de médicos, profesionales y horarios",
        "especialidades": "Especialidades médicas del centro de salud",
        "administracion": "Información administrativa, actas y tareas",
        "presupuestos": "Presupuestos y cotizaciones oficiales en PDF",
    }
    for m in modules:
        desc = module_descriptions.get(m, "Módulo administrativo operativo")
        mod_rows.append(f"| `{m}/` | {desc} |")

    file_rows = []
    for p in sorted(STORAGE.rglob("*")):
        if p.is_file() and p.name != "INDEX.md":
            rel = str(p.relative_to(STORAGE)).replace("\\", "/")
            dt = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            desc = describe_file(p.name)
            file_rows.append(f"| `{rel}` | {dt} | {desc} |")

    global_text = (
        "# Índice Global Maestro · files_storage\n\n"
        f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        "## Módulos y Subcarpetas\n"
        "| Módulo | Función |\n|---|---|\n"
        + ("\n".join(mod_rows) if mod_rows else "| `(ninguno)` | - |")
        + "\n\n"
        "## Archivos Físicos Registrados\n"
        "| Archivo | Última Modificación | Descripción |\n|---|---|---|\n"
        + ("\n".join(file_rows) if file_rows else "| *(sin archivos)* | - | - |")
        + "\n"
    )
    root_index.write_text(global_text, encoding="utf-8")

def list_files(module=""):
    """
    Lista archivos como cadenas de texto relativas (compatibilidad hacia atrás).
    """
    path = ensure_module(module)
    result = []
    for p in sorted(path.rglob("*")):
        if p.is_file():
            result.append(str(p.relative_to(path)).replace("\\", "/"))
    return result

def list_files_detailed(module=""):
    """
    Lista archivos con metadatos completos para el explorador del panel.
    """
    STORAGE.mkdir(parents=True, exist_ok=True)
    result = []
    # Escaneamos files_storage
    for p in sorted(STORAGE.rglob("*")):
        if p.is_file():
            stat = p.stat()
            rel = str(p.relative_to(STORAGE)).replace("\\", "/")
            parts = Path(rel).parts
            mod_name = parts[0] if len(parts) > 1 else "(raíz)"

            if module and mod_name != module:
                continue

            size_bytes = stat.st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

            result.append({
                "name": p.name,
                "rel_path": rel,
                "module": mod_name,
                "size_bytes": size_bytes,
                "size_str": size_str,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
                "is_pdf": p.name.lower().endswith(".pdf"),
                "is_editable": p.name.lower().endswith((".txt", ".md", ".json")),
                "download_url": f"/api/files/download/?path={rel}",
            })
    return result

def read_file(filename, module=""):
    safe = safe_name(filename)
    # Puede ser ruta relativa directa en files_storage o dentro del módulo
    if (STORAGE / safe).is_file():
        path = STORAGE / safe
    else:
        path = ensure_module(module) / safe

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Archivo no encontrado: {filename}")
    return path.read_text(encoding="utf-8", errors="replace")

def write_file(filename, content, module=""):
    safe = safe_name(filename)
    # Si filename ya incluye una carpeta (ej: "presupuestos/algo.txt"), respetarla desde STORAGE
    if "/" in safe:
        path = STORAGE / safe
    elif module:
        path = ensure_module(module) / safe
    else:
        path = STORAGE / safe

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(content), encoding="utf-8")
    
    # Determinar qué módulo actualizar
    mod_to_update = module or (safe.split("/")[0] if "/" in safe else "")
    update_index(mod_to_update)
    return str(path.relative_to(STORAGE)).replace("\\", "/")

def delete_file(filename, module=""):
    safe = safe_name(filename)
    if (STORAGE / safe).is_file():
        path = STORAGE / safe
    else:
        path = ensure_module(module) / safe

    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {filename}")
    if path.is_dir():
        raise ValueError("No se puede eliminar un directorio directamente con delete_file.")
    path.unlink()
    
    mod_to_update = module or (safe.split("/")[0] if "/" in safe else "")
    update_index(mod_to_update)
    return f"Archivo {filename} eliminado correctamente."

def append_memory(note, module=""):
    path = ensure_module(module) / "MEMORY.md"
    current = path.read_text(encoding="utf-8")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_entry = f"- [{stamp}] {note.strip()}\n"
    path.write_text(current.rstrip() + "\n" + new_entry, encoding="utf-8")

    # Si se agregó a un módulo y no al global, también dejamos constancia en el global
    if module:
        global_path = ensure_module("") / "MEMORY.md"
        g_current = global_path.read_text(encoding="utf-8")
        global_path.write_text(g_current.rstrip() + f"\n- [{stamp}] [{module}] {note.strip()}\n", encoding="utf-8")

    return True

def get_memory_content(module=""):
    path = ensure_module(module) / "MEMORY.md"
    return path.read_text(encoding="utf-8")

def create_subfolder(name, description=""):
    name = safe_name(name)
    if "/" in name:
        raise ValueError("El módulo debe ser una carpeta de primer nivel (sin subrutas).")
    path = ensure_module(name)
    memory = path / "MEMORY.md"
    current = memory.read_text(encoding="utf-8")
    if description:
        memory.write_text(current + f"\n## Descripción del Módulo\n{description}\n", encoding="utf-8")
    update_index(name)
    return name

def history_path(module=""):
    return ensure_module(module) / "CHAT_HISTORY.json"

def load_history(module=""):
    try:
        return json.loads(history_path(module).read_text(encoding="utf-8"))
    except Exception:
        return []

def save_history(history, module=""):
    history_path(module).write_text(
        json.dumps(history[-30:], ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def clear_history(module=""):
    history_path(module).write_text("[]", encoding="utf-8")
    return True

def system_prompt():
    if CLAUDE_MD.exists():
        return CLAUDE_MD.read_text(encoding="utf-8")
    return "Eres el Asistente del Panel Administrativo de UMSA. Gestiona archivos en files_storage/."

def tools():
    return [
        {
            "name": "read_file",
            "description": "Lee el contenido de un archivo físico dentro de files_storage/. Solo lee archivos existentes.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Nombre o ruta relativa del archivo a leer (ej: 'prueba.txt' o 'turnos/agenda.md')"}
                },
                "required": ["filename"]
            }
        },
        {
            "name": "write_file",
            "description": "Crea o modifica un archivo físico real dentro de files_storage/ y actualiza automáticamente INDEX.md.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Nombre o ruta relativa del archivo (ej: 'tareasfuturas.md', 'prueba.txt', o 'administracion/acta.md')"},
                    "content": {"type": "string", "description": "Contenido completo a escribir en el archivo"}
                },
                "required": ["filename", "content"]
            }
        },
        {
            "name": "delete_file",
            "description": "Elimina un archivo físico de files_storage/ cuando corresponda y actualiza automáticamente INDEX.md.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Nombre o ruta relativa del archivo a eliminar"}
                },
                "required": ["filename"]
            }
        },
        {
            "name": "append_memory",
            "description": "Agrega una regla permanente, directiva o nota obligatoria a MEMORY.md persistente.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "note": {"type": "string", "description": "Regla permanente o nota a registrar"}
                },
                "required": ["note"]
            }
        },
        {
            "name": "create_subfolder",
            "description": "Crea un nuevo módulo / subcarpeta en files_storage/ con su estructura (INDEX.md, MEMORY.md, CHAT_HISTORY.json).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "folder_name": {"type": "string", "description": "Nombre de la subcarpeta o módulo (ej: 'presupuestos', 'guardias')"},
                    "description": {"type": "string", "description": "Propósito o descripción del módulo"}
                },
                "required": ["folder_name"]
            }
        },
        {
            "name": "list_files",
            "description": "Lista los archivos físicos registrados en files_storage/ del módulo actual o de todo el sistema.",
            "input_schema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "create_presupuesto",
            "description": "Genera un presupuesto en PDF profesional para un médico o cliente profesional y lo guarda físicamente en files_storage/presupuestos/. REGLA: NO inventar precios. Si falta el precio unitario, pedirlo antes de llamar a esta herramienta.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "cliente": {"type": "string", "description": "Nombre del médico o cliente profesional (ej: 'Dr. Juan Pérez')"},
                    "institucion": {"type": "string", "description": "Nombre de la institución médica o clínica (opcional)"},
                    "productos": {
                        "type": "array",
                        "description": "Lista de productos cotizados",
                        "items": {
                            "type": "object",
                            "properties": {
                                "descripcion": {"type": "string", "description": "Nombre / detalle del producto"},
                                "cantidad": {"type": "number", "description": "Cantidad de unidades"},
                                "precio_unitario": {"type": "number", "description": "Precio unitario (REQUERIDO - NO inventar)"}
                            },
                            "required": ["descripcion", "cantidad", "precio_unitario"]
                        }
                    },
                    "observaciones": {"type": "string", "description": "Condiciones y notas administrativas"},
                    "validez": {"type": "string", "description": "Plazo de validez (ej: '15 días corridos')"},
                    "iva_porcentaje": {"type": "number", "description": "Porcentaje de IVA (ej: 21.0)"}
                },
                "required": ["cliente", "productos"]
            }
        },
        {
            "name": "update_index",
            "description": "Reconstruye y actualiza el archivo INDEX.md del módulo o el índice maestro global files_storage/INDEX.md.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "module": {"type": "string", "description": "Nombre del módulo a actualizar (opcional, dejar vacío para global)"}
                }
            }
        }
    ]

def execute_tool(name, inp, module):
    if name == "read_file":
        return read_file(inp["filename"], module)
    if name == "write_file":
        saved_path = write_file(inp["filename"], inp["content"], module)
        return f"Archivo físico guardado correctamente: {saved_path}. INDEX.md ha sido actualizado."
    if name == "delete_file":
        return delete_file(inp["filename"], module)
    if name == "append_memory":
        append_memory(inp["note"], module)
        return f"Regla permanente agregada a MEMORY.md: '{inp['note']}'"
    if name == "create_subfolder":
        folder = create_subfolder(inp["folder_name"], inp.get("description", ""))
        return f"Módulo creado físicamente: files_storage/{folder}/ (con INDEX.md, MEMORY.md y CHAT_HISTORY.json)"
    if name == "list_files":
        return list_files(module)
    if name == "update_index":
        target_mod = inp.get("module", module)
        update_index(target_mod)
        return f"INDEX.md actualizado correctamente para '{target_mod or 'global'}'."
    if name == "create_presupuesto":
        from .presupuestos import generate_presupuesto_pdf
        res = generate_presupuesto_pdf(
            cliente=inp["cliente"],
            productos=inp["productos"],
            institucion=inp.get("institucion", ""),
            observaciones=inp.get("observaciones", ""),
            validez=inp.get("validez", "15 días corridos"),
            iva_porcentaje=inp.get("iva_porcentaje", 21.0),
        )
        return (
            f"Presupuesto {res['numero']} generado exitosamente.\n"
            f"- Archivo físico: {res['rel_path']}\n"
            f"- Subtotal: $ {res['subtotal']:,.2f}\n"
            f"- IVA ({res['iva_porcentaje']}%): $ {res['iva_monto']:,.2f}\n"
            f"- TOTAL: $ {res['total']:,.2f}\n"
            f"- Descarga: {res['download_url']}"
        )
    raise ValueError(f"Herramienta desconocida: {name}")


def get_modules_summary():
    """
    Retorna un resumen de cada módulo para la visualización del panel administrativo.
    """
    STORAGE.mkdir(parents=True, exist_ok=True)
    mods = []
    module_descriptions = {
        "turnos": "Gestión y agendas de turnos médicos",
        "pacientes": "Información administrativa de pacientes",
        "profesionales": "Nómina de médicos, profesionales y horarios",
        "especialidades": "Especialidades médicas del centro de salud",
        "administracion": "Información administrativa, actas y tareas",
        "presupuestos": "Presupuestos y cotizaciones oficiales en PDF",
        "insumos": "Gestión operativa de insumos descartables",
        "pagos": "Medios de pago oficiales, pasarelas digitales, promociones y cobranzas",
    }

    for d in sorted(STORAGE.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            files = [f for f in d.rglob("*") if f.is_file()]
            total_size = sum(f.stat().st_size for f in files)
            if total_size < 1024:
                size_str = f"{total_size} B"
            elif total_size < 1024 * 1024:
                size_str = f"{total_size / 1024:.1f} KB"
            else:
                size_str = f"{total_size / (1024 * 1024):.1f} MB"

            mods.append({
                "name": d.name,
                "description": module_descriptions.get(d.name, "Módulo de gestión administrativa"),
                "file_count": len(files),
                "total_size": size_str,
                "has_index": (d / "INDEX.md").exists(),
                "has_memory": (d / "MEMORY.md").exists(),
                "has_history": (d / "CHAT_HISTORY.json").exists(),
            })
    return mods


def get_system_status():
    """
    Recopila información del estado del sistema real sin inventar datos.
    """
    import django
    from .umsa import status as umsa_status

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    claude_connected = bool(api_key and api_key.startswith("sk-ant-"))
    claude_model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    is_docker = os.path.exists("/.dockerenv") or os.getenv("RUNNING_IN_DOCKER") == "1"

    total_files = len([p for p in STORAGE.rglob("*") if p.is_file()])
    total_mods = len(list_modules())
    has_global_index = (STORAGE / "INDEX.md").exists()
    has_global_memory = (STORAGE / "MEMORY.md").exists()
    presupuestos_count = len(list((STORAGE / "presupuestos").glob("*.pdf"))) if (STORAGE / "presupuestos").exists() else 0

    return {
        "django_version": django.get_version(),
        "is_docker": is_docker,
        "claude_connected": claude_connected,
        "claude_model": claude_model,
        "total_files": total_files,
        "total_modules": total_mods,
        "presupuestos_count": presupuestos_count,
        "has_global_index": has_global_index,
        "has_global_memory": has_global_memory,
        "umsa": umsa_status(),
    }


DEFAULT_INVENTARIO = [
    {
        "id": 1,
        "producto": "Guantes látex descartables",
        "presentacion": "Caja x 100 U",
        "precio_unitario": 2500,
        "stock": "ILIMITADO",
        "estado": "Disponible",
        "imagen": "/media/productos/1_guantes_latex.jpg"
    },
    {
        "id": 2,
        "producto": "Jeringas descartables",
        "presentacion": "Caja x 50 U",
        "precio_unitario": 3500,
        "stock": "ILIMITADO",
        "estado": "Disponible",
        "imagen": "/media/productos/2_jeringas.jpg"
    },
    {
        "id": 3,
        "producto": "Rollo de gasa",
        "presentacion": "90 cm x 100 m",
        "precio_unitario": 1200,
        "stock": "ILIMITADO",
        "estado": "Disponible",
        "imagen": "/media/productos/3_rollo_gasa.jpg"
    },
    {
        "id": 4,
        "producto": "Paquete algodón",
        "presentacion": "200 g",
        "precio_unitario": 1000,
        "stock": "ILIMITADO",
        "estado": "Disponible",
        "imagen": "/media/productos/4_paquete_algodon.jpg"
    },
    {
        "id": 5,
        "producto": "Alcohol antiséptico",
        "presentacion": "100 ml",
        "precio_unitario": 3000,
        "stock": "ILIMITADO",
        "estado": "Disponible",
        "imagen": "/media/productos/5_alcohol_antiseptico.jpg"
    },
    {
        "id": 6,
        "producto": "Agua oxigenada",
        "presentacion": "100 ml",
        "precio_unitario": 3000,
        "stock": "ILIMITADO",
        "estado": "Disponible",
        "imagen": "/media/productos/6_agua_oxigenada.jpg"
    },
    {
        "id": 7,
        "producto": "Barbijos descartables",
        "presentacion": "Caja x 50 unidades",
        "precio_unitario": 2500,
        "stock": "ILIMITADO",
        "estado": "Disponible",
        "imagen": "/media/productos/7_barbijos_descartables.jpg"
    },
    {
        "id": 8,
        "producto": "Cinta adhesiva hipoalergénica",
        "presentacion": "Rollo x 1 unidad",
        "precio_unitario": 1500,
        "stock": "ILIMITADO",
        "estado": "Disponible",
        "imagen": "/media/productos/8_cinta_adhesiva.svg"
    },
    {
        "id": 9,
        "producto": "Cofias descartables",
        "presentacion": "Paquete x 100 unidades",
        "precio_unitario": 3000,
        "stock": "ILIMITADO",
        "estado": "Disponible",
        "imagen": "/media/productos/9_cofias_descartables.svg"
    },
    {
        "id": 10,
        "producto": "Camisolines descartables",
        "presentacion": "Paquete x 10 unidades",
        "precio_unitario": 8000,
        "stock": "ILIMITADO",
        "estado": "Disponible",
        "imagen": "/media/productos/10_camisolines_descartables.svg"
    },
]

def save_inventario(items: list):
    """Guarda la lista de insumos en files_storage/inventario.json y actualiza el índice."""
    inv_path = STORAGE / "inventario.json"
    inv_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        update_index("")
    except Exception:
        pass

def get_inventario():
    """
    Retorna el inventario oficial de insumos médicos desde files_storage/inventario.json.
    Si no existe o si faltan productos de la lista oficial de 10 insumos,
    los incorpora sin duplicar ni pisar precios o imágenes editadas por el usuario.
    """
    inv_path = STORAGE / "inventario.json"
    data = []
    if inv_path.exists():
        try:
            raw = json.loads(inv_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                data = raw
        except Exception:
            data = []

    existing_ids = {it.get("id") for it in data if isinstance(it, dict) and "id" in it}
    existing_names = {it.get("producto", "").strip().lower() for it in data if isinstance(it, dict)}

    modified = False
    # Asegurar que cada producto existente tenga su campo imagen
    for it in data:
        if not it.get("imagen"):
            matching_default = next((d for d in DEFAULT_INVENTARIO if d["id"] == it.get("id")), None)
            if matching_default:
                it["imagen"] = matching_default["imagen"]
            else:
                it["imagen"] = "/media/productos/placeholder.svg"
            modified = True

    # Agregar insumos faltantes de los 10 oficiales
    for default_item in DEFAULT_INVENTARIO:
        if default_item["id"] not in existing_ids and default_item["producto"].strip().lower() not in existing_names:
            data.append(dict(default_item))
            existing_ids.add(default_item["id"])
            modified = True

    if modified or not inv_path.exists():
        save_inventario(data)

    return data

def update_or_create_inventario_item(data: dict, image_file=None, remove_image=False) -> dict:
    """
    Crea o actualiza un insumo en el inventario oficial.
    Permite subir una imagen física o quitar la existente volviendo al placeholder.
    """
    items = get_inventario()
    item_id = data.get("id")
    try:
        item_id = int(item_id) if item_id else None
    except (ValueError, TypeError):
        item_id = None

    target = None
    if item_id:
        target = next((it for it in items if it.get("id") == item_id), None)

    if not target:
        max_id = max((it.get("id", 0) for it in items), default=0)
        item_id = max_id + 1
        target = {
            "id": item_id,
            "producto": str(data.get("producto", "")).strip() or f"Insumo #{item_id}",
            "presentacion": str(data.get("presentacion", "")).strip() or "Unidad",
            "precio_unitario": float(data.get("precio_unitario", 0) or 0),
            "stock": str(data.get("stock", "ILIMITADO")).strip() or "ILIMITADO",
            "estado": str(data.get("estado", "Disponible")).strip() or "Disponible",
            "imagen": "/media/productos/placeholder.svg",
        }
        items.append(target)
    else:
        if "producto" in data and str(data["producto"]).strip():
            target["producto"] = str(data["producto"]).strip()
        if "presentacion" in data:
            target["presentacion"] = str(data["presentacion"]).strip()
        if "precio_unitario" in data:
            try:
                target["precio_unitario"] = float(data["precio_unitario"])
            except (ValueError, TypeError):
                pass
        if "stock" in data and str(data["stock"]).strip():
            target["stock"] = str(data["stock"]).strip()
        if "estado" in data and str(data["estado"]).strip():
            target["estado"] = str(data["estado"]).strip()

    if remove_image:
        target["imagen"] = "/media/productos/placeholder.svg"
    elif image_file:
        media_dir = STORAGE / "media" / "productos"
        media_dir.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(image_file.name)[1].lower() or ".jpg"
        clean_prod_name = re.sub(r"[^\w]+", "_", target["producto"].lower()).strip("_")
        fname = f"item_{item_id}_{clean_prod_name}{ext}"
        file_path = media_dir / fname
        with open(file_path, "wb") as f:
            for chunk in image_file.chunks():
                f.write(chunk)
        target["imagen"] = f"/media/productos/{fname}"

    save_inventario(items)
    return target

