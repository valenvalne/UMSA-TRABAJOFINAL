import os
import uuid
import logging
import requests
from datetime import datetime
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .models import Turno

logger = logging.getLogger(__name__)

DEFAULT_APPS_SCRIPT_URL = (
    "https://script.google.com/macros/s/AKfycbzMm1Z-NmUE7eyaySRKPYLTjYInRB4JpY_1gybHAiXHTZmBJs8n7O_8J5poovR2wOS1/exec"
)

AUTHORIZED_USERS = {
    "valentinagalo12@gmail.com": "1234",
    "mauriciocasals90@gmail.com": "1234",
}


def inicio(request):
    """
    Vista principal de la web de UMSA Centro Médico.
    Protegida por AuthRequiredMiddleware.
    """
    return render(request, 'medico/index.html')


def login_view(request):
    """
    Pantalla previa de autenticación requerida para acceder a toda la plataforma.
    Credenciales autorizadas:
      Email: valentinagalo12@gmail.com
      Password: 1234
    """
    is_authenticated = (
        request.session.get('authenticated_user', '').lower() in AUTHORIZED_USERS or
        (request.user.is_authenticated and (
            request.user.username.lower() in AUTHORIZED_USERS or 
            request.user.email.lower() in AUTHORIZED_USERS
        ))
    )
    if is_authenticated:
        return redirect('/')

    error = None
    email_val = ''

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        email_val = email

        if email in AUTHORIZED_USERS and AUTHORIZED_USERS[email] == password:
            request.session['authenticated_user'] = email
            user = authenticate(request, username=email, password=password)
            if user:
                login(request, user)
            next_url = request.GET.get('next') or request.POST.get('next') or '/'
            return redirect(next_url)
        else:
            error = 'Credenciales no válidas. Verifique su correo electrónico y contraseña.'

    return render(request, 'medico/login.html', {
        'error': error,
        'email': email_val,
        'next': request.GET.get('next', '')
    })


def logout_view(request):
    """
    Cierre de sesión y redirección a la pantalla de login.
    """
    request.session.flush()
    logout(request)
    return redirect('/login/')


def crear_turno(request):
    """
    Creación y confirmación de turno.
    Sincroniza con Google Sheets (Google Apps Script) y persiste en Django.
    """
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        dni = request.POST.get('dni', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        especialidad = request.POST.get('especialidad', '').strip()
        profesional = request.POST.get('profesional', '').strip()
        fecha_str = request.POST.get('fecha', '').strip()
        hora_str = request.POST.get('hora', '').strip()

        if not all([nombre, dni, telefono, especialidad, profesional, fecha_str, hora_str]):
            return JsonResponse({
                'ok': False,
                'error': 'Todos los campos son obligatorios.'
            }, status=400)

        try:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            hora_obj = datetime.strptime(hora_str, '%H:%M').time()
        except ValueError:
            return JsonResponse({
                'ok': False,
                'error': 'Formato de fecha u hora no válido.'
            }, status=400)

        id_generado = f"UMSA-{uuid.uuid4().hex[:8].upper()}"
        sheets_synced = False

        # 1. Enviar a Google Sheets vía Google Apps Script Web App
        apps_script_url = getattr(
            settings,
            'GOOGLE_APPS_SCRIPT_URL',
            os.environ.get('GOOGLE_APPS_SCRIPT_URL', DEFAULT_APPS_SCRIPT_URL)
        )
        try:
            payload = {
                'action': 'create',
                'token': '',
                'nombre': nombre,
                'dni': dni,
                'telefono': telefono,
                'especialidad': especialidad,
                'profesional': profesional,
                'fecha': fecha_str,
                'hora': hora_str,
            }
            res = requests.post(
                apps_script_url,
                json=payload,
                headers={'Content-Type': 'text/plain;charset=utf-8'},
                timeout=12
            )
            if res.ok:
                data_gs = res.json()
                if data_gs.get('ok'):
                    sheets_synced = True
                    if data_gs.get('idTurno'):
                        id_generado = data_gs['idTurno']
                    logger.info(f"Turno sincronizado con Google Sheets exitosamente: {id_generado}")
                else:
                    logger.warning(f"Google Apps Script respondió con error: {data_gs.get('message')}")
            else:
                logger.warning(f"Google Apps Script HTTP status: {res.status_code}")
        except Exception as exc:
            logger.error(f"Excepción al conectar con Google Apps Script: {exc}")

        # 2. Guardar en Base de Datos de Django
        turno = Turno.objects.create(
            id_turno=id_generado,
            nombre=nombre,
            dni=dni,
            telefono=telefono,
            especialidad=especialidad,
            profesional=profesional,
            fecha=fecha_obj,
            hora=hora_obj,
        )

        return JsonResponse({
            'ok': True,
            'id_turno': turno.id_turno,
            'sheets_synced': sheets_synced,
        })

    return JsonResponse({
        'ok': False,
        'error': 'Método no permitido.'
    }, status=405)
