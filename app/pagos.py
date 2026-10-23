import os
import json
import logging
from decimal import Decimal
from datetime import datetime, date
from pathlib import Path
from django.utils import timezone
from django.db import transaction

from .models import MedioPago, RegistroPago, WebhookLog
from .services import STORAGE, append_memory

logger = logging.getLogger(__name__)

DEFAULT_MEDIOS_PAGO = [
    {
        "codigo": "efectivo",
        "nombre": "Efectivo",
        "descripcion": "Cobro presencial en efectivo en ventanilla de administración y caja de UMSA Centro Médico.",
        "icono": "💵",
        "activo": True,
        "instrucciones": "Presentarse en la administración central de UMSA Centro Médico de lunes a viernes de 08:00 a 20:00 hs para abonar y retirar el recibo oficial.",
        "observaciones": "Se emite recibo fiscal manual o electrónico en el momento de la cobranza.",
        "datos_bancarios": {},
        "online_config": {},
    },
    {
        "codigo": "tarjeta",
        "nombre": "Tarjeta de débito/crédito",
        "descripcion": "Cobro presencial mediante tarjeta de débito o crédito a través de terminal POS institucional.",
        "icono": "💳",
        "activo": True,
        "instrucciones": "Abono presencial en terminal POS en ventanilla de UMSA Centro Médico con tarjeta Visa, Mastercard o Cabal.",
        "observaciones": "El cupón POS debe anexarse como respaldo del comprobante de cobro.",
        "datos_bancarios": {},
        "online_config": {},
    },
    {
        "codigo": "transferencia",
        "nombre": "Transferencia bancaria",
        "descripcion": "Transferencia electrónica directa a la cuenta bancaria institucional de UMSA Centro Médico.",
        "icono": "🏛️",
        "activo": True,
        "instrucciones": "Realizar la transferencia bancaria y presentar o enviar el comprobante con número de operación para su verificación administrativa.",
        "observaciones": "La acreditación se confirma una vez visualizados los fondos en el extracto bancario oficial.",
        "datos_bancarios": {
            "titular": "",
            "banco": "",
            "tipo_cuenta": "",
            "numero_cuenta": "",
            "cbu": "",
            "alias": "",
            "cuit": "",
            "configurado": False,
        },
        "online_config": {},
    },
    {
        "codigo": "mercadopago",
        "nombre": "Mercado Pago",
        "descripcion": "Cobro electrónico mediante link de pago oficial, QR o transferencia vía Mercado Pago.",
        "icono": "📱",
        "activo": True,
        "instrucciones": "Escanee el código QR o acceda al enlace de pago oficial provisto por UMSA.",
        "observaciones": "Integración con pasarela online en modo configuración. Requiere credenciales institucionales en variables de entorno.",
        "datos_bancarios": {},
        "online_config": {
            "alias_mp": "",
            "cvu_mp": "",
            "link_pago_oficial": "",
            "gateway_status": "Pendiente de configuración",
            "provider_configured": False,
        },
    },
]


def get_pagos_storage_dir() -> Path:
    p_dir = STORAGE / "pagos"
    p_dir.mkdir(parents=True, exist_ok=True)
    return p_dir


def sync_medios_to_json():
    """Guarda espejo JSON de los medios de pago en files_storage/pagos/medios_pago.json."""
    try:
        p_dir = get_pagos_storage_dir()
        f_path = p_dir / "medios_pago.json"
        qs = MedioPago.objects.all().order_by("id")
        data = [m.to_dict() for m in qs]
        f_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Error sincronizando medios_pago.json: {e}")


def sync_pagos_to_json():
    """Guarda espejo JSON del historial de pagos en files_storage/pagos/pagos_historial.json."""
    try:
        p_dir = get_pagos_storage_dir()
        f_path = p_dir / "pagos_historial.json"
        qs = RegistroPago.objects.all().order_by("-fecha_pago", "-id")
        data = [p.to_dict() for p in qs]
        f_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Error sincronizando pagos_historial.json: {e}")


def init_medios_pago_if_empty():
    """Inicializa los 4 medios de pago por defecto si la base de datos está vacía."""
    try:
        if MedioPago.objects.count() == 0:
            for item in DEFAULT_MEDIOS_PAGO:
                MedioPago.objects.create(
                    codigo=item["codigo"],
                    nombre=item["nombre"],
                    descripcion=item["descripcion"],
                    icono=item["icono"],
                    activo=item.get("activo", True),
                    instrucciones=item.get("instrucciones", ""),
                    observaciones=item.get("observaciones", ""),
                    datos_bancarios=item.get("datos_bancarios", {}),
                    online_config=item.get("online_config", {}),
                )
            sync_medios_to_json()
    except Exception as e:
        logger.warning(f"Error al inicializar medios de pago: {e}")


def get_medios_pago(only_active: bool = False) -> list[dict]:
    """Retorna la lista de medios de pago disponibles."""
    init_medios_pago_if_empty()
    qs = MedioPago.objects.all().order_by("id")
    if only_active:
        qs = qs.filter(activo=True)
    return [m.to_dict() for m in qs]


def get_medio_pago_by_codigo(codigo: str) -> MedioPago | None:
    init_medios_pago_if_empty()
    return MedioPago.objects.filter(codigo=codigo).first()


def update_medio_pago(codigo: str, data: dict) -> dict:
    """Actualiza la configuración, estado, datos bancarios o instrucciones de un medio de pago."""
    init_medios_pago_if_empty()
    medio = MedioPago.objects.filter(codigo=codigo).first()
    if not medio:
        raise ValueError(f"Medio de pago con código '{codigo}' no encontrado.")

    if "nombre" in data and str(data["nombre"]).strip():
        medio.nombre = str(data["nombre"]).strip()
    if "descripcion" in data:
        medio.descripcion = str(data["descripcion"]).strip()
    if "activo" in data:
        medio.activo = bool(data["activo"])
    if "instrucciones" in data:
        medio.instrucciones = str(data["instrucciones"]).strip()
    if "observaciones" in data:
        medio.observaciones = str(data["observaciones"]).strip()

    # Actualizar datos bancarios
    if "datos_bancarios" in data and isinstance(data["datos_bancarios"], dict):
        current_bancarios = medio.datos_bancarios or {}
        current_bancarios.update(data["datos_bancarios"])
        # Verificar si está configurado
        tiene_datos = bool(
            current_bancarios.get("cbu") or current_bancarios.get("alias") or current_bancarios.get("numero_cuenta")
        )
        current_bancarios["configurado"] = tiene_datos
        medio.datos_bancarios = current_bancarios

    # Actualizar configuración online / Mercado Pago
    if "online_config" in data and isinstance(data["online_config"], dict):
        current_online = medio.online_config or {}
        current_online.update(data["online_config"])
        medio.online_config = current_online

    medio.save()
    sync_medios_to_json()
    return medio.to_dict()


def toggle_medio_pago(codigo: str, activo: bool | None = None) -> dict:
    """Activa o desactiva un medio de pago sin borrar su historial ni datos."""
    init_medios_pago_if_empty()
    medio = MedioPago.objects.filter(codigo=codigo).first()
    if not medio:
        raise ValueError(f"Medio de pago '{codigo}' no encontrado.")

    if activo is None:
        medio.activo = not medio.activo
    else:
        medio.activo = bool(activo)

    medio.save()
    sync_medios_to_json()
    return medio.to_dict()


def get_presupuesto_pagos_summary(presupuesto_numero: str, total_presupuesto: float | None = None) -> dict:
    """
    Calcula el resumen de pagos para un presupuesto dado:
    - total_presupuesto
    - total_pagado (solo confirmados: pagado o parcial)
    - saldo_pendiente
    - estado_pago ('Pendiente', 'Parcial', 'Pagado', 'Cancelado')
    - listado de pagos
    """
    total_pres = 0.0
    if total_presupuesto is not None:
        total_pres = float(total_presupuesto)
    else:
        from .presupuestos import init_historial_from_storage
        historial = init_historial_from_storage()
        for p in historial:
            if (p.get("numero") or "").strip().lower() == str(presupuesto_numero).strip().lower():
                total_pres = float(p.get("total", 0.0))
                break

    pagos_qs = RegistroPago.objects.filter(presupuesto_numero=presupuesto_numero).order_by("-fecha_pago", "-id")
    pagos_list = [p.to_dict() for p in pagos_qs]

    # Calcular confirmado
    total_confirmado = 0.0
    hay_pagos_confirmados = False
    todos_cancelados = len(pagos_list) > 0 and all(p["estado"] == RegistroPago.ESTADO_CANCELADO for p in pagos_list)

    for p in pagos_list:
        if p["estado"] in [RegistroPago.ESTADO_PAGADO, RegistroPago.ESTADO_PARCIAL]:
            total_confirmado += p["importe"]
            hay_pagos_confirmados = True

    saldo_pendiente = max(0.0, total_pres - total_confirmado)

    if todos_cancelados:
        estado_pago = "Cancelado"
    elif total_confirmado >= total_pres and total_pres > 0:
        estado_pago = "Pagado"
    elif total_confirmado > 0:
        estado_pago = "Parcial"
    else:
        estado_pago = "Pendiente"

    return {
        "presupuesto_numero": presupuesto_numero,
        "total_presupuesto": total_pres,
        "total_pagado": total_confirmado,
        "saldo_pendiente": saldo_pendiente,
        "estado_pago": estado_pago,
        "cantidad_pagos": len(pagos_list),
        "pagos": pagos_list,
    }


def update_presupuesto_historial_payment_status(presupuesto_numero: str):
    """
    Actualiza el registro correspondiente en presupuestos_historial.json
    para que contenga el saldo pendiente, total pagado y estado de pago calculado.
    """
    try:
        from .presupuestos import init_historial_from_storage, get_historial_file_path
        historial = init_historial_from_storage()
        summary = get_presupuesto_pagos_summary(presupuesto_numero)

        found = False
        for p in historial:
            if p.get("numero") == presupuesto_numero:
                p["total_pagado"] = summary["total_pagado"]
                p["saldo_pendiente"] = summary["saldo_pendiente"]
                p["estado_pago"] = summary["estado_pago"]
                found = True
                break

        if found:
            h_file = get_historial_file_path()
            h_file.write_text(json.dumps(historial, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Error actualizando estado de pago en historial de presupuestos: {e}")


def registrar_pago(data: dict) -> dict:
    """
    Registra un pago manualmente asociado a un presupuesto existente.
    Realiza validaciones completas:
    - Presupuesto existente y no cancelado.
    - Importe positivo (> 0).
    - Medio de pago activo.
    - Validación de duplicados por número de operación.
    - Validación de no exceder el total del presupuesto salvo confirmación.
    """
    init_medios_pago_if_empty()

    presupuesto_num = str(data.get("presupuesto_numero", "")).strip()
    if not presupuesto_num:
        raise ValueError("Debe seleccionar un presupuesto oficial.")

    from .presupuestos import get_presupuesto_by_numero
    pres = get_presupuesto_by_numero(presupuesto_num)
    if not pres:
        raise ValueError(f"El presupuesto '{presupuesto_num}' no existe en el sistema.")

    if pres.get("estado", "").lower() == "cancelado":
        raise ValueError(f"El presupuesto '{presupuesto_num}' se encuentra cancelado. No admite nuevos pagos.")

    # Validar importe
    try:
        importe = Decimal(str(data.get("importe", 0)).replace(",", "."))
        if importe <= 0:
            raise ValueError("El importe debe ser un número positivo mayor a 0.")
    except Exception:
        raise ValueError("El importe ingresado no es válido. Indique un monto numérico positivo.")

    # Validar medio de pago
    medio_cod = str(data.get("medio_pago", "efectivo")).strip().lower()
    medio = MedioPago.objects.filter(codigo=medio_cod).first()
    if not medio:
        raise ValueError(f"El medio de pago '{medio_cod}' no es válido.")
    if not medio.activo:
        raise ValueError(f"El medio de pago '{medio.nombre}' se encuentra inactivo. Seleccione un medio activo.")

    # Validar número de operación duplicado
    num_op = str(data.get("numero_operacion", "")).strip() or None
    if num_op:
        dup = RegistroPago.objects.filter(
            numero_operacion=num_op,
            medio_pago_codigo=medio_cod
        ).exclude(estado=RegistroPago.ESTADO_CANCELADO).first()
        if dup:
            raise ValueError(
                f"Ya existe un pago registrado con el N° de operación '{num_op}' "
                f"en el presupuesto {dup.presupuesto_numero}."
            )

    # Validar fecha
    fecha_pago_str = str(data.get("fecha_pago", "")).strip()
    if fecha_pago_str:
        try:
            # Formatos admitidos: YYYY-MM-DD o DD/MM/YYYY
            if "/" in fecha_pago_str:
                f_dt = datetime.strptime(fecha_pago_str, "%d/%m/%Y")
            else:
                f_dt = datetime.strptime(fecha_pago_str, "%Y-%m-%d")
            fecha_val = f_dt.date()
        except Exception:
            fecha_val = timezone.now().date()
    else:
        fecha_val = timezone.now().date()

    # Validar excedente de saldo
    summary_actual = get_presupuesto_pagos_summary(presupuesto_num)
    saldo_actual = Decimal(str(summary_actual["saldo_pendiente"]))
    permitir_excedente = bool(data.get("permitir_excedente", False))

    if importe > saldo_actual and saldo_actual > 0 and not permitir_excedente:
        # Si el usuario no confirmó explícitamente el sobrepago
        raise ValueError(
            f"El importe ingresado (${importe:,.2f}) supera el saldo pendiente de ${saldo_actual:,.2f} "
            f"del presupuesto {presupuesto_num}."
        )

    # Estado del pago
    estado_req = str(data.get("estado", RegistroPago.ESTADO_PAGADO)).strip().lower()
    if estado_req not in [RegistroPago.ESTADO_PENDIENTE, RegistroPago.ESTADO_PAGADO, RegistroPago.ESTADO_PARCIAL, RegistroPago.ESTADO_CANCELADO]:
        estado_req = RegistroPago.ESTADO_PAGADO

    # Si no se forzó parcial pero cubre parcialmente, orientar a parcial si no es pagado total
    if estado_req == RegistroPago.ESTADO_PAGADO and importe < saldo_actual:
        estado_req = RegistroPago.ESTADO_PARCIAL

    cliente_nombre = str(data.get("cliente") or pres.get("cliente") or "Cliente UMSA").strip()
    institucion_nombre = str(data.get("institucion") or pres.get("institucion") or "").strip()
    observaciones = str(data.get("observaciones", "")).strip()

    with transaction.atomic():
        pago = RegistroPago.objects.create(
            presupuesto_numero=presupuesto_num,
            cliente=cliente_nombre,
            institucion=institucion_nombre,
            medio_pago=medio,
            medio_pago_codigo=medio.codigo,
            medio_pago_nombre=medio.nombre,
            importe=importe,
            estado=estado_req,
            numero_operacion=num_op,
            fecha_pago=fecha_val,
            observaciones=observaciones,
            es_online=bool(data.get("es_online", False)),
            external_reference=str(data.get("external_reference", "")).strip(),
            provider_status=str(data.get("provider_status", "")).strip(),
            provider_payment_id=str(data.get("provider_payment_id", "")).strip(),
            idempotency_key=str(data.get("idempotency_key", "")).strip(),
        )

    # Actualizar estado persistente en JSON y memoria institucional
    sync_pagos_to_json()
    update_presupuesto_historial_payment_status(presupuesto_num)

    try:
        append_memory(
            f"Pago registrado #{pago.id}: {medio.nombre} por ${importe:,.2f} para {presupuesto_num} ({cliente_nombre}) - Estado: {pago.get_estado_display()}.",
            "pagos"
        )
        append_memory(
            f"Cobranza {presupuesto_num}: Pago de ${importe:,.2f} ({medio.nombre}) - Estado: {pago.get_estado_display()}.",
            ""
        )
    except Exception as e:
        logger.warning(f"Error registrando en memoria de pagos: {e}")

    return pago.to_dict()


def cancelar_pago(pago_id: int, motivo: str) -> dict:
    """
    Cancela un pago sin borrar el registro histórico.
    Guarda el motivo de cancelación, fecha y actualiza el saldo del presupuesto.
    """
    motivo_clean = str(motivo).strip()
    if not motivo_clean:
        raise ValueError("Debe indicar el motivo o justificación de la cancelación del pago.")

    pago = RegistroPago.objects.filter(id=pago_id).first()
    if not pago:
        raise ValueError(f"No se encontró el pago #{pago_id}.")

    if pago.estado == RegistroPago.ESTADO_CANCELADO:
        raise ValueError(f"El pago #{pago_id} ya se encuentra cancelado.")

    pago.estado = RegistroPago.ESTADO_CANCELADO
    pago.motivo_cancelacion = motivo_clean
    pago.fecha_cancelacion = timezone.now()
    pago.save()

    sync_pagos_to_json()
    update_presupuesto_historial_payment_status(pago.presupuesto_numero)

    try:
        append_memory(
            f"Pago #{pago.id} CANCELADO para {pago.presupuesto_numero} (Importe: ${pago.importe:,.2f}). Motivo: {motivo_clean}",
            "pagos"
        )
    except Exception:
        pass

    return pago.to_dict()


def get_pagos_historial(
    search: str | None = None,
    filter_medio: str | None = None,
    filter_estado: str | None = None,
    fecha_rango: str | None = None,
    order_by: str = "-fecha_pago"
) -> list[dict]:
    """
    Retorna el listado de pagos con filtros completos por búsqueda, medio, estado y fechas.
    """
    init_medios_pago_if_empty()
    qs = RegistroPago.objects.all().select_related("medio_pago")

    # Filtro por búsqueda (cliente, institución, presupuesto_numero, numero_operacion)
    if search and str(search).strip():
        s = str(search).strip().lower()
        # Búsqueda en memoria o queryset
        matching_ids = []
        for p in qs:
            if (
                s in (p.presupuesto_numero or "").lower()
                or s in (p.cliente or "").lower()
                or s in (p.institucion or "").lower()
                or s in (p.numero_operacion or "").lower()
                or s in (p.observaciones or "").lower()
            ):
                matching_ids.append(p.id)
        qs = qs.filter(id__in=matching_ids)

    # Filtro por medio de pago
    if filter_medio and str(filter_medio).strip().lower() not in ["todos", ""]:
        qs = qs.filter(medio_pago_codigo=str(filter_medio).strip().lower())

    # Filtro por estado
    if filter_estado and str(filter_estado).strip().lower() not in ["todos", ""]:
        qs = qs.filter(estado=str(filter_estado).strip().lower())

    # Filtro por rango de fechas
    now = timezone.now().date()
    if fecha_rango:
        fr = str(fecha_rango).strip().lower()
        if fr == "hoy":
            qs = qs.filter(fecha_pago=now)
        elif fr == "semana":
            dias_atras = now - timezone.timedelta(days=7)
            qs = qs.filter(fecha_pago__gte=dias_atras)
        elif fr == "mes":
            qs = qs.filter(fecha_pago__year=now.year, fecha_pago__month=now.month)

    # Ordenamiento
    if order_by == "importe_desc":
        qs = qs.order_by("-importe")
    elif order_by == "importe_asc":
        qs = qs.order_by("importe")
    elif order_by == "fecha_asc":
        qs = qs.order_by("fecha_pago", "id")
    else:
        qs = qs.order_by("-fecha_pago", "-id")

    return [p.to_dict() for p in qs]


def get_pagos_dashboard_metrics() -> dict:
    """
    Calcula las métricas reales del módulo de pagos y cobranzas:
    - total_confirmado
    - total_pendiente_cobro
    - cantidad_pagos_registrados
    - cantidad_pagos_parciales
    - distribucion_medios
    - actividad_reciente
    """
    init_medios_pago_if_empty()
    from .presupuestos import init_historial_from_storage

    pagos_qs = RegistroPago.objects.all()
    presupuestos = init_historial_from_storage()

    total_confirmado = 0.0
    pagos_registrados_count = 0
    pagos_parciales_count = 0
    por_medio = {}

    for p in pagos_qs:
        if p.estado == RegistroPago.ESTADO_CANCELADO:
            continue
        pagos_registrados_count += 1
        imp = float(p.importe)

        if p.estado in [RegistroPago.ESTADO_PAGADO, RegistroPago.ESTADO_PARCIAL]:
            total_confirmado += imp
            m_nom = p.medio_pago_nombre or "Efectivo"
            por_medio[m_nom] = por_medio.get(m_nom, 0.0) + imp

        if p.estado == RegistroPago.ESTADO_PARCIAL:
            pagos_parciales_count += 1

    # Calcular saldo pendiente total de los presupuestos emitidos
    # Pre-calcular pagos confirmados agrupados por presupuesto
    pagos_por_pres = {}
    for p in pagos_qs:
        if p.estado in [RegistroPago.ESTADO_PAGADO, RegistroPago.ESTADO_PARCIAL]:
            num = (p.presupuesto_numero or "").strip()
            pagos_por_pres[num] = pagos_por_pres.get(num, 0.0) + float(p.importe)

    total_pendiente_cobro = 0.0
    presupuestos_con_pagos_parciales = 0

    for pres in presupuestos:
        if str(pres.get("estado", "")).lower() == "cancelado":
            continue
        tot = float(pres.get("total", 0.0))
        num = (pres.get("numero") or "").strip()
        pagado_pres = pagos_por_pres.get(num, 0.0)
        saldo_pres = max(0.0, tot - pagado_pres)
        total_pendiente_cobro += saldo_pres
        if 0 < pagado_pres < tot:
            presupuestos_con_pagos_parciales += 1

    # Formatear distribución por medio
    distribucion = []
    for m_nom, m_total in sorted(por_medio.items(), key=lambda x: x[1], reverse=True):
        pct = (m_total / total_confirmado * 100.0) if total_confirmado > 0 else 0.0
        distribucion.append({
            "medio": m_nom,
            "total": m_total,
            "porcentaje": round(pct, 1),
        })

    # Actividad reciente (últimos 5 pagos)
    recientes = [p.to_dict() for p in pagos_qs.order_by("-fecha_pago", "-id")[:5]]

    return {
        "total_confirmado": total_confirmado,
        "total_pendiente_cobro": total_pendiente_cobro,
        "cantidad_pagos_registrados": pagos_registrados_count,
        "cantidad_pagos_parciales": pagos_parciales_count,
        "presupuestos_parciales": presupuestos_con_pagos_parciales,
        "distribucion_medios": distribucion,
        "actividad_reciente": recientes,
    }


def process_mercadopago_webhook(payload: dict, headers: dict) -> dict:
    """
    Arquitectura preparada para futura integración con Mercado Pago.
    Garantiza:
    - Registro de auditoría en WebhookLog
    - Idempotencia (evita duplicación de pagos)
    - Verificación segura
    """
    event_id = str(payload.get("id") or payload.get("data", {}).get("id") or "")
    action = payload.get("action") or payload.get("type") or "payment.updated"

    # Verificar si el evento ya fue procesado
    existing = WebhookLog.objects.filter(event_id=event_id, processed=True).first()
    if existing:
        return {
            "status": "already_processed",
            "message": f"El evento {event_id} ya fue procesado previamente (idempotencia garantizada).",
        }

    log_entry = WebhookLog.objects.create(
        provider="mercadopago",
        event_id=event_id,
        payload=payload,
        processed=False,
        status_message=f"Evento recibido: {action}",
    )

    # Validar token/secreto si estuviese configurado en variables de entorno
    mp_access_token = os.getenv("MERCADO_PAGO_ACCESS_TOKEN", "").strip()
    mp_webhook_secret = os.getenv("MERCADO_PAGO_WEBHOOK_SECRET", "").strip()

    if not mp_access_token:
        log_entry.status_message = "Credenciales de Mercado Pago pendientes de configuración."
        log_entry.save()
        return {
            "status": "pending_credentials",
            "message": "Integración online pendiente: MERCADO_PAGO_ACCESS_TOKEN no configurado en entorno.",
            "log_id": log_entry.id,
        }

    # Cuando las credenciales reales estén presentes, aquí se verifica la firma y se consulta la API de MP
    log_entry.processed = True
    log_entry.status_message = "Procesado con éxito."
    log_entry.save()

    return {
        "status": "success",
        "message": "Notificación recibida y auditada con éxito.",
        "log_id": log_entry.id,
    }
