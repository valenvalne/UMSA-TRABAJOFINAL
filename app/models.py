from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

class MedioPago(models.Model):
    """
    Representa un medio de pago institucional de UMSA Centro Médico.
    Los cuatro medios oficiales son:
    1. Efectivo
    2. Tarjeta de débito/crédito
    3. Transferencia bancaria
    4. Mercado Pago
    """
    codigo = models.SlugField(max_length=50, unique=True, help_text="Identificador único del medio de pago")
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, default="")
    icono = models.CharField(max_length=10, default="💳")
    activo = models.BooleanField(default=True, help_text="Indica si el medio está disponible para nuevos pagos")
    instrucciones = models.TextField(blank=True, default="", help_text="Instrucciones para el cliente/profesional")
    observaciones = models.TextField(blank=True, default="", help_text="Notas administrativas internas")
    
    # Configuración bancaria oficial (para Transferencia bancaria)
    datos_bancarios = models.JSONField(
        default=dict, 
        blank=True, 
        help_text="Datos bancarios oficiales: titular, banco, tipo_cuenta, numero_cuenta, cbu, alias, cuit"
    )
    
    # Configuración para pagos electrónicos / Mercado Pago
    online_config = models.JSONField(
        default=dict, 
        blank=True, 
        help_text="Configuración de cobro electrónico: link_pago_oficial, alias_mp, cvu_mp, etc."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Medio de Pago"
        verbose_name_plural = "Medios de Pago"

    def __str__(self):
        return f"{self.nombre} ({'Activo' if self.activo else 'Inactivo'})"

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "icono": self.icono,
            "activo": self.activo,
            "instrucciones": self.instrucciones,
            "observaciones": self.observaciones,
            "datos_bancarios": self.datos_bancarios or {},
            "online_config": self.online_config or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RegistroPago(models.Model):
    """
    Registro administrativo de pago vinculado a un presupuesto oficial de UMSA.
    """
    ESTADO_PENDIENTE = "pendiente"
    ESTADO_PAGADO = "pagado"
    ESTADO_PARCIAL = "parcial"
    ESTADO_CANCELADO = "cancelado"

    ESTADOS_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_PAGADO, "Pagado"),
        (ESTADO_PARCIAL, "Parcial"),
        (ESTADO_CANCELADO, "Cancelado"),
    ]

    presupuesto_numero = models.CharField(max_length=60, db_index=True, help_text="Número oficial del presupuesto (ej: UMSA-P-2026-0001)")
    cliente = models.CharField(max_length=200, help_text="Nombre del cliente o profesional")
    institucion = models.CharField(max_length=200, blank=True, default="", help_text="Institución o clínica")
    
    medio_pago = models.ForeignKey(
        MedioPago, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="pagos",
        help_text="Medio de pago utilizado"
    )
    medio_pago_codigo = models.CharField(max_length=50, default="efectivo")
    medio_pago_nombre = models.CharField(max_length=100, default="Efectivo")
    
    importe = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Importe abonado en este registro"
    )
    
    estado = models.CharField(max_length=20, choices=ESTADOS_CHOICES, default=ESTADO_PAGADO)
    numero_operacion = models.CharField(max_length=120, blank=True, null=True, db_index=True, help_text="N° de comprobante, ticket POS o transferencia")
    fecha_pago = models.DateField(default=timezone.now, help_text="Fecha en que se efectuó el pago")
    observaciones = models.TextField(blank=True, default="", help_text="Observaciones administrativas")
    
    # Registro de cancelación (nunca se borra silenciosamente)
    motivo_cancelacion = models.TextField(blank=True, default="")
    fecha_cancelacion = models.DateTimeField(blank=True, null=True)
    
    # Preparación para futura integración online (Mercado Pago u otros proveedores)
    es_online = models.BooleanField(default=False, help_text="True si proviene de pasarela de pago online verificada")
    external_reference = models.CharField(max_length=150, blank=True, default="", db_index=True)
    provider_status = models.CharField(max_length=50, blank=True, default="")
    provider_payment_id = models.CharField(max_length=120, blank=True, default="", db_index=True)
    idempotency_key = models.CharField(max_length=150, blank=True, default="", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_pago", "-id"]
        verbose_name = "Registro de Pago"
        verbose_name_plural = "Registros de Pago"

    def __str__(self):
        return f"Pago #{self.id} - {self.presupuesto_numero} - ${self.importe} ({self.estado})"

    def to_dict(self):
        return {
            "id": self.id,
            "presupuesto_numero": self.presupuesto_numero,
            "cliente": self.cliente,
            "institucion": self.institucion,
            "medio_pago_codigo": self.medio_pago_codigo,
            "medio_pago_nombre": self.medio_pago_nombre,
            "medio_pago_icono": self.medio_pago.icono if self.medio_pago else "💳",
            "importe": float(self.importe),
            "estado": self.estado,
            "estado_display": dict(self.ESTADOS_CHOICES).get(self.estado, self.estado.title()),
            "numero_operacion": self.numero_operacion or "",
            "fecha_pago": self.fecha_pago.strftime("%d/%m/%Y") if self.fecha_pago else "",
            "fecha_pago_iso": self.fecha_pago.isoformat() if self.fecha_pago else "",
            "observaciones": self.observaciones or "",
            "motivo_cancelacion": self.motivo_cancelacion or "",
            "fecha_cancelacion": self.fecha_cancelacion.isoformat() if self.fecha_cancelacion else None,
            "es_online": self.es_online,
            "external_reference": self.external_reference or "",
            "provider_status": self.provider_status or "",
            "provider_payment_id": self.provider_payment_id or "",
            "idempotency_key": self.idempotency_key or "",
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%d/%m/%Y %H:%M") if self.updated_at else "",
        }


class WebhookLog(models.Model):
    """
    Registro y auditoría de eventos de notificación externa para pasarelas online.
    Garantiza idempotencia y trazabilidad de eventos.
    """
    provider = models.CharField(max_length=50, default="mercadopago")
    event_id = models.CharField(max_length=150, blank=True, default="", db_index=True)
    payload = models.JSONField(default=dict)
    processed = models.BooleanField(default=False)
    status_message = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Log de Webhook"
        verbose_name_plural = "Logs de Webhook"

    def __str__(self):
        return f"Webhook [{self.provider}] {self.event_id} ({'Procesado' if self.processed else 'Pendiente'})"
