/**
 * ===================================================================
 * UMSA - CENTRO MÉDICO ("APOSTÁ A LA VIDA")
 * Lógica exclusiva de la Terminal y Panel Privado Kiosco (kiosco.html)
 * ===================================================================
 */

document.addEventListener("DOMContentLoaded", () => {
  // URL exacta de Google Apps Script configurada en el proyecto (desde app.js)
  const GOOGLE_APPS_SCRIPT_URL =
    "https://script.google.com/macros/s/AKfycbzMm1Z-NmUE7eyaySRKPYLTjYInRB4JpY_1gybHAiXHTZmBJs8n7O_8J5poovR2wOS1/exec";

  // Clave obligatoria de almacenamiento local
  const KIOSCO_SESSION_KEY = "KIOSCO_SESSION";

  // Elementos del DOM - Login
  const loginSection = document.getElementById("kiosco-login-section");
  const loginForm = document.getElementById("kiosco-login-form");
  const emailInput = document.getElementById("kiosk-email");
  const passwordInput = document.getElementById("kiosk-password");
  const btnTogglePwd = document.getElementById("btn-toggle-password");
  const loginError = document.getElementById("kiosk-login-error");
  const btnLoginSubmit = document.getElementById("btn-login-submit");

  // Elementos del DOM - Panel Privado
  const privateSection = document.getElementById("kiosco-private-section");
  const userEmailDisplay = document.getElementById("kiosk-user-email");
  const userRoleDisplay = document.getElementById("kiosk-user-role");
  const btnLogout = document.getElementById("btn-kiosk-logout");

  // Elementos del DOM - Consulta de Turnos en Kiosco
  const lookupForm = document.getElementById("kiosk-lookup-form");
  const searchDniInput = document.getElementById("kiosk-search-dni");
  const btnSearch = document.getElementById("btn-kiosk-search");
  const searchError = document.getElementById("kiosk-search-error");
  const searchResult = document.getElementById("kiosk-search-result");

  // 1. Alternar visibilidad de contraseña (inicialmente oculta)
  if (btnTogglePwd && passwordInput) {
    btnTogglePwd.addEventListener("click", () => {
      const isPassword = passwordInput.getAttribute("type") === "password";
      passwordInput.setAttribute("type", isPassword ? "text" : "password");
      btnTogglePwd.setAttribute(
        "aria-label",
        isPassword ? "Ocultar contraseña" : "Mostrar contraseña"
      );
      btnTogglePwd.setAttribute(
        "title",
        isPassword ? "Ocultar contraseña" : "Mostrar contraseña"
      );
      const icon = btnTogglePwd.querySelector(".pwd-icon");
      if (icon) {
        icon.textContent = isPassword ? "🙈" : "👁";
      }
    });
  }

  // 2. Envío del formulario de Login Kiosco
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      await iniciarSesionKiosco();
    });
  }

  // 3. Botón Cerrar Sesión
  if (btnLogout) {
    btnLogout.addEventListener("click", () => {
      cerrarSesionKiosco(false);
    });
  }

  // 4. Consulta de Turnos en Panel Privado
  if (lookupForm) {
    lookupForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      await consultarTurnoKiosco();
    });
  }

  // ===================================================================
  // FUNCIONES DE AUTENTICACIÓN Y SESIÓN
  // ===================================================================

  /**
   * Muestra la pantalla de login y oculta el panel privado
   */
  function mostrarLoginKiosco(mensajeError = "") {
    if (privateSection) privateSection.hidden = true;
    if (loginSection) loginSection.hidden = false;
    if (mensajeError) {
      mostrarMensaje(loginError, mensajeError);
    } else {
      limpiarMensaje(loginError);
    }
  }

  /**
   * Envía las credenciales al endpoint de Google Apps Script (action: "login")
   */
  async function iniciarSesionKiosco() {
    limpiarMensaje(loginError);
    limpiarEstadoInvalido(emailInput);
    limpiarEstadoInvalido(passwordInput);

    const email = String(emailInput?.value || "").trim().toLowerCase();
    const password = String(passwordInput?.value || "");

    if (!email || !password) {
      if (!email) marcarInvalido(emailInput);
      if (!password) marcarInvalido(passwordInput);
      mostrarMensaje(loginError, "Por favor completá correo y contraseña.");
      return;
    }

    const textoOriginal = btnLoginSubmit.textContent;
    btnLoginSubmit.disabled = true;
    btnLoginSubmit.textContent = "INGRESANDO…";

    try {
      // Envío de credenciales a Google Apps Script
      const result = await enviarPeticionAppsScript({
        action: "login",
        email: email,
        password: password
      });

      if (result && result.ok && result.token) {
        const userEmail =
          result.email || (result.user && result.user.email) || email;
        const userRole =
          result.role ||
          result.rol ||
          (result.user && (result.user.rol || result.user.role)) ||
          "Kiosco";

        // Guardar sesión en localStorage (NUNCA guardar contraseña)
        guardarSesionLocal({
          token: result.token,
          email: userEmail,
          role: userRole,
          expiration: result.expiration || null
        });

        // Verificación estricta en servidor antes de desplegar el panel privado
        await verificarYMostrarPanelKiosco(result.token);

        if (loginForm) {
          loginForm.reset();
        }
      } else {
        const errorMsg =
          (result && (result.message || result.error)) ||
          "Email o contraseña incorrectos.";
        mostrarMensaje(loginError, errorMsg);
        marcarInvalido(emailInput);
        marcarInvalido(passwordInput);
      }
    } catch (err) {
      console.error("Error al conectar con Google Apps Script:", err);
      mostrarMensaje(
        loginError,
        "No pudimos conectar con el servidor de autenticación. Intentá nuevamente."
      );
    } finally {
      btnLoginSubmit.disabled = false;
      btnLoginSubmit.textContent = textoOriginal;
    }
  }

  /**
   * Valida obligatoriamente el token con Google Apps Script (action: "verify_session")
   * y autoriza el acceso al panel privado únicamente si el servidor confirma:
   * result.ok === true && (result.authenticated === true || result.valid === true) && role === "Kiosco"
   */
  async function verificarYMostrarPanelKiosco(token) {
    if (!token) {
      cerrarSesionKiosco(false);
      return;
    }

    try {
      const result = await enviarPeticionAppsScript({
        action: "verify_session",
        token: token
      });

      const isOk = Boolean(result && result.ok);
      const isAuthenticated = Boolean(
        result && (result.authenticated === true || result.valid === true)
      );
      const userRole = String(
        (result && (result.role || result.rol)) ||
        (result && result.user && (result.user.rol || result.user.role)) ||
        ""
      ).trim().toLowerCase();

      if (isOk && isAuthenticated && userRole === "kiosco") {
        // Sesión confirmada por el servidor
        const email =
          result.email ||
          (result.user && result.user.email) ||
          "valentinagalo12@gmail.com";

        if (userEmailDisplay) userEmailDisplay.textContent = email;
        if (userRoleDisplay) userRoleDisplay.textContent = "Kiosco";

        // Mostrar Panel Privado y ocultar Login
        if (loginSection) loginSection.hidden = true;
        if (privateSection) {
          privateSection.hidden = false;
          privateSection.scrollIntoView({ behavior: "smooth", block: "start" });
        }
        if (searchDniInput) {
          setTimeout(() => searchDniInput.focus(), 150);
        }
      } else {
        // Sesión inválida, expirada o rol no autorizado
        console.warn("Sesión no autorizada o expirada en el servidor.");
        cerrarSesionKiosco(true);
      }
    } catch (err) {
      console.error("Error al verificar sesión con Google Apps Script:", err);
      cerrarSesionKiosco(false);
      mostrarMensaje(
        loginError,
        "No se pudo verificar la sesión. Por favor ingresá nuevamente."
      );
    }
  }

  /**
   * Cierra la sesión, limpia localStorage y vuelve a la pantalla de login
   */
  function cerrarSesionKiosco(porExpiracion = false) {
    try {
      localStorage.removeItem(KIOSCO_SESSION_KEY);
    } catch (e) {
      console.warn("Error al remover sesión local:", e);
    }

    if (privateSection) privateSection.hidden = true;
    if (searchResult) searchResult.innerHTML = "";
    if (searchDniInput) searchDniInput.value = "";
    limpiarMensaje(searchError);

    mostrarLoginKiosco(
      porExpiracion
        ? "Tu sesión expiró. Por favor iniciá sesión nuevamente."
        : ""
    );
  }

  /**
   * Guarda los datos de sesión en localStorage (NUNCA almacena contraseña)
   */
  function guardarSesionLocal(sessionData) {
    try {
      localStorage.setItem(KIOSCO_SESSION_KEY, JSON.stringify(sessionData));
    } catch (e) {
      console.warn("No se pudo guardar la sesión en localStorage:", e);
    }
  }

  /**
   * Obtiene y parsea la sesión almacenada en localStorage
   */
  function getLocalSession() {
    try {
      const raw = localStorage.getItem(KIOSCO_SESSION_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  // ===================================================================
  // CONSULTA DE TURNOS EN MODO KIOSCO (action: "lookup")
  // ===================================================================

  async function consultarTurnoKiosco() {
    limpiarMensaje(searchError);
    limpiarEstadoInvalido(searchDniInput);
    if (searchResult) searchResult.innerHTML = "";

    const dni = String(searchDniInput?.value || "").replace(/\D/g, "");

    if (!dni || dni.length < 7 || dni.length > 8) {
      marcarInvalido(searchDniInput);
      mostrarMensaje(searchError, "Ingresá un DNI válido de 7 u 8 números.");
      if (searchDniInput) searchDniInput.focus();
      return;
    }

    const session = getLocalSession();
    const token = (session && session.token) || "";

    const textoOriginal = btnSearch.textContent;
    btnSearch.disabled = true;
    btnSearch.textContent = "Buscando…";

    try {
      const result = await enviarPeticionAppsScript({
        action: "lookup",
        token: token,
        dni: dni
      });

      let foundAppt = null;
      if (result) {
        if (result.appointment) foundAppt = result.appointment;
        else if (result.data) foundAppt = result.data;
        else if (result.turno) foundAppt = result.turno;
        else if (Array.isArray(result.turnos) && result.turnos.length > 0)
          foundAppt = result.turnos[0];
        else if (Array.isArray(result.rows) && result.rows.length > 0)
          foundAppt = result.rows[0];
        else if (result.nombre || result.dni) foundAppt = result;
      }

      if (result && result.ok && result.found !== false && foundAppt) {
        renderizarTurnoKiosco(foundAppt);
      } else {
        searchResult.innerHTML = `
          <div class="kiosco-empty-result" role="status">
            No se encontraron turnos registrados para el DNI <strong>${escapeHtml(dni)}</strong>.
          </div>
        `;
      }
    } catch (err) {
      console.error("Error al consultar turno en Kiosco:", err);
      mostrarMensaje(
        searchError,
        "No pudimos consultar la agenda médica. Intentá nuevamente."
      );
    } finally {
      btnSearch.disabled = false;
      btnSearch.textContent = textoOriginal;
    }
  }

  function renderizarTurnoKiosco(appt) {
    const idTurno = escapeHtml(appt.idTurno || appt.id || "-");
    const dni = escapeHtml(appt.dni || "");
    const nombre = escapeHtml(appt.nombre || "-");
    const telefono = escapeHtml(appt.telefono || "-");
    const especialidad = escapeHtml(appt.especialidad || "-");
    const profesional = escapeHtml(appt.profesional || "-");
    const fecha = formatearFecha(appt.fecha);
    const hora = escapeHtml(appt.hora || appt.horario || "-");
    const estado = escapeHtml(appt.estado || "Solicitud recibida");

    searchResult.innerHTML = `
      <div class="kiosco-result-card" role="region" aria-label="Turno encontrado">
        <div class="kiosco-result-header">
          <h4>Paciente: ${nombre}</h4>
          <span class="badge-status">${estado}</span>
        </div>
        <dl class="kiosco-appt-detail">
          <div><dt>ID Turno</dt><dd>${idTurno}</dd></div>
          <div><dt>DNI</dt><dd>${dni}</dd></div>
          <div><dt>Teléfono</dt><dd>${telefono}</dd></div>
          <div><dt>Especialidad</dt><dd>${especialidad}</dd></div>
          <div><dt>Profesional</dt><dd>${profesional}</dd></div>
          <div><dt>Fecha</dt><dd>${fecha}</dd></div>
          <div><dt>Horario</dt><dd>${hora} hs.</dd></div>
          <div><dt>Estado</dt><dd>${estado}</dd></div>
        </dl>
      </div>
    `;
  }

  // ===================================================================
  // COMUNICACIÓN HTTP DIRECTA CON GOOGLE APPS SCRIPT
  // ===================================================================

  async function enviarPeticionAppsScript(payload) {
    const response = await fetch(GOOGLE_APPS_SCRIPT_URL, {
      method: "POST",
      headers: {
        "Content-Type": "text/plain;charset=utf-8"
      },
      body: JSON.stringify(payload),
      redirect: "follow"
    });

    if (!response.ok) {
      throw new Error(`HTTP Error ${response.status}`);
    }

    const data = await response.json();
    return data;
  }

  // ===================================================================
  // FUNCIONES AUXILIARES
  // ===================================================================

  function marcarInvalido(el) {
    if (el) el.setAttribute("aria-invalid", "true");
  }

  function limpiarEstadoInvalido(el) {
    if (el) el.removeAttribute("aria-invalid");
  }

  function mostrarMensaje(container, texto) {
    if (!container) return;
    container.textContent = texto;
    container.hidden = false;
  }

  function limpiarMensaje(container) {
    if (!container) return;
    container.hidden = true;
    container.textContent = "";
  }

  function formatearFecha(fechaStr) {
    if (!fechaStr) return "-";
    const parts = String(fechaStr).split(/[-/]/);
    if (parts.length === 3) {
      if (parts[0].length === 4) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
      }
      return `${parts[0]}/${parts[1]}/${parts[2]}`;
    }
    return fechaStr;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // ===================================================================
  // AL CARGAR LA PÁGINA: VERIFICACIÓN OBLIGATORIA CON APPS SCRIPT
  // ===================================================================
  const savedSession = getLocalSession();
  if (savedSession && savedSession.token) {
    // Verificar sesión existente contra el servidor
    verificarYMostrarPanelKiosco(savedSession.token);
  } else {
    // Si no hay sesión, mostrar la pantalla de login
    mostrarLoginKiosco();
  }
});
