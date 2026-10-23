import os
import requests

def umsa_base_url():
    return os.getenv("UMSA_BASE_URL", "https://umsa-trabajofinal.onrender.com").rstrip("/")

def known_create_turno_url():
    return umsa_base_url() + os.getenv("UMSA_CREAR_TURNO_PATH", "/crear-turno/")

def status():
    try:
        r = requests.get(umsa_base_url() + "/", timeout=4)
        return {"online": r.ok, "status_code": r.status_code, "url": umsa_base_url()}
    except requests.RequestException as exc:
        return {"online": False, "error": str(exc), "url": umsa_base_url()}

def create_turno_note():
    # El endpoint conocido de UMSA usa POST y protección CSRF en el formulario.
    # Por seguridad, no se intenta hacer un POST ciego desde este proyecto.
    return {
        "configured": bool(os.getenv("UMSA_TURNOS_API_URL")),
        "base_url": umsa_base_url(),
        "known_endpoint": known_create_turno_url(),
        "message": "Para operaciones automáticas de turnos se recomienda exponer una API JSON autenticada en UMSA-Django."
    }
