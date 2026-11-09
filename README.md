# UMSA · Centro Médico & Panel Administrativo con IA (Trabajo Final)

Sistema integral de **UMSA Centro Médico ("Apostá a la vida")** que integra en una única plataforma:
1. **Sitio Web Público Oficial de UMSA Turnos:** Solicitud y consulta de turnos médicos en línea, cartilla de profesionales por especialidad, opiniones comunitarias y terminal Kiosco.
2. **Panel Administrativo con IA:** Asistente inteligente (Claude, Gemini, Groq, OpenAI), generación de presupuestos con cálculo de IVA y emisión en PDF, catálogo oficial de insumos médicos (stock ilimitado), módulo integral de medios de pago y cobranzas (Efectivo, Tarjeta, Transferencia, Mercado Pago con Webhook) y persistencia real en `files_storage/` con `INDEX.md` y `MEMORY.md`.
3. **Pestaña Interactiva Integrada:** Visualización y prueba del sitio web de turnos directamente dentro del panel administrativo sin abandonar la sesión.

---

## 🌐 Enlaces de Acceso

### En Producción (Render):
- **Sitio Web Público UMSA Turnos:** `https://umsa-trabajofinal.onrender.com/`
- **Panel Administrativo con IA:** `https://umsa-trabajofinal.onrender.com/panel/`
- **Terminal Kiosco:** `https://umsa-trabajofinal.onrender.com/kiosco/`

### En Desarrollo Local:
- **Sitio Web Principal:** `http://localhost:8000/`
- **Panel Administrativo con IA:** `http://localhost:8000/panel/`
- **Página Web Completa (Directa):** `http://localhost:8000/sitio/`
- **Terminal Kiosco:** `http://localhost:8000/kiosco/`

---

## 🔑 Credenciales de Acceso

El sistema cuenta con autenticación segura para administradores y rol Kiosco:

- **Email:** `valentinagalo12@gmail.com`
- **Contraseña:** `1234`
*(Usuario secundario docente: `mauriciocasals90@gmail.com` / `1234`)*

---

## 🚀 Puesta en Marcha Local

### Opción 1: Con Python directo
```bash
# 1. Configurar variables de entorno
copy .env.example .env

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Aplicar migraciones
python manage.py migrate

# 4. Iniciar servidor
python manage.py runserver 127.0.0.1:8000
```

### Opción 2: Con Docker Compose
```bash
docker compose up --build
```

---

## 🏗️ Arquitectura y Tecnologías
- **Backend:** Django 5 + Python 3.13 + Gunicorn + WhiteNoise.
- **Base de Datos:** SQLite (Local) / PostgreSQL con `dj_database_url` (Producción Render).
- **Frontend:** HTML5 semántico, CSS3 moderno responsivo, JavaScript ES6+.
- **Inteligencia Artificial:** Soporte Multi-Proveedor (Anthropic Claude, Google Gemini, Groq LLaMA 3.3, OpenAI).
- **Almacenamiento y Auditoría:** Persistencia física real en `files_storage/`, `INDEX.md`, `MEMORY.md` y `pagos_historial.json`.
- **Integración Externa:** Sincronización en vivo con Google Apps Script y Google Sheets para turnos médicos.
