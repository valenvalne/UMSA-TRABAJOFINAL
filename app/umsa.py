import os
import requests

def umsa_base_url():
    return os.getenv("UMSA_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

def known_create_turno_url():
    return umsa_base_url() + os.getenv("UMSA_CREAR_TURNO_PATH", "/crear-turno/")

def status():
    # Sistema local integrado (sin dependencia de servidores externos ni Render)
    return {
        "online": True,
        "status_code": 200,
        "url": umsa_base_url(),
        "local": True
    }

def create_turno_note():
    return {
        "configured": True,
        "base_url": umsa_base_url(),
        "known_endpoint": known_create_turno_url(),
        "message": "Sistema de turnos integrado localmente en este mismo servidor (/crear-turno/)."
    }
