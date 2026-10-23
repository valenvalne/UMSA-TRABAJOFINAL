from django.contrib import admin
from .models import MedioPago, RegistroPago, WebhookLog

@admin.register(MedioPago)
class MedioPagoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "icono", "activo", "updated_at")
    list_filter = ("activo",)
    search_fields = ("nombre", "codigo", "descripcion")

@admin.register(RegistroPago)
class RegistroPagoAdmin(admin.ModelAdmin):
    list_display = ("id", "presupuesto_numero", "cliente", "medio_pago_nombre", "importe", "estado", "fecha_pago", "es_online")
    list_filter = ("estado", "medio_pago_codigo", "es_online", "fecha_pago")
    search_fields = ("presupuesto_numero", "cliente", "institucion", "numero_operacion")
    readonly_fields = ("created_at", "updated_at")

@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "event_id", "processed", "status_message", "created_at")
    list_filter = ("provider", "processed")
    search_fields = ("event_id", "status_message")
