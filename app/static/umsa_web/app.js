/**
 * ===================================================================
 * UMSA - CENTRO MÉDICO ("APOSTÁ A LA VIDA")
 * Lógica interactiva, validaciones, gestión de turnos y sistema Kiosco.
 *
 * Arquitectura:
 * Frontend Web -> Sistema de autenticación Kiosco -> Google Apps Script -> Google Sheets
 * Backend Google Apps Script Web App:
 * https://script.google.com/macros/s/AKfycbzMm1Z-NmUE7eyaySRKPYLTjYInRB4JpY_1gybHAiXHTZmBJs8n7O_8J5poovR2wOS1/exec
 * Hoja de cálculo: Pestaña "Hoja 1" (Columnas A - I: REGISTRO, ID TURNO, NOMBRE, DNI, TELEFONO, ESPECIALIDAD, PROFESIONAL, FECHA, HORA)
 * ===================================================================
 */

document.addEventListener("DOMContentLoaded", () => {
  // Conexión directa a Google Apps Script Web App
  const APPS_SCRIPT_URL =
    "https://script.google.com/macros/s/AKfycbzMm1Z-NmUE7eyaySRKPYLTjYInRB4JpY_1gybHAiXHTZmBJs8n7O_8J5poovR2wOS1/exec";

  const SESSION_STORAGE_KEY = "umsa_kiosk_session";

  // Mapeo obligatorio: Especialidad -> Profesional asignado
  const SPECIALTY_DOCTOR_MAP = {
    "Clínica Médica": "Dr. Lecouna",
    "Odontología": "Dr. Ortega",
    "Reumatología": "Dr. Fullop",
    "Neurología": "Dr. Devechi"
  };

  // Elementos principales del DOM
  const interactiveArea = document.querySelector(".interactive-area");
  const turnoPanel = document.getElementById("turno-panel");
  const consultaPanel = document.getElementById("consulta-panel");
  const confirmacionPanel = document.getElementById("confirmacion");
  const confirmacionDetalle = document.getElementById("confirmacion-detalle");

  const turnoForm = document.getElementById("turno-form");
  const turnoError = document.getElementById("turno-error");
  const especialidadSelect = document.getElementById("especialidad");
  const profesionalInput = document.getElementById("profesional");
  const fechaInput = document.getElementById("fecha");

  const consultaForm = document.getElementById("consulta-form");
  const consultaError = document.getElementById("consulta-error");
  const consultaResultado = document.getElementById("consulta-resultado");

  // Elementos de autenticación y panel Kiosco
  const kioskLoginPanel = document.getElementById("kiosk-login-panel");
  const kioskLoginForm = document.getElementById("kiosk-login-form");
  const kioskLoginError = document.getElementById("kiosk-login-error");
  const kioskPrivatePanel = document.getElementById("kiosk-private-panel");
  const kioskUserEmail = document.getElementById("kiosk-user-email");
  const btnKioskLogout = document.getElementById("btn-kiosk-logout");
  const btnKioskTrigger = document.getElementById("btn-kiosk-trigger");
  const btnFooterKiosk = document.getElementById("btn-footer-kiosk");
  const kioskLookupForm = document.getElementById("kiosk-lookup-form");
  const kioskSearchError = document.getElementById("kiosk-search-error");
  const kioskSearchResult = document.getElementById("kiosk-search-result");
  const btnKioskCrearTurno = document.getElementById("btn-kiosk-crear-turno");

  // 1. Establecer fecha mínima en el selector de fecha (hoy)
  if (fechaInput) {
    const today = new Date().toISOString().split("T")[0];
    fechaInput.min = today;
  }

  // 2. Autocompletado reactivo de profesional según especialidad seleccionada
  if (especialidadSelect && profesionalInput) {
    especialidadSelect.addEventListener("change", () => {
      const selectedSpecialty = especialidadSelect.value;
      profesionalInput.value = SPECIALTY_DOCTOR_MAP[selectedSpecialty] || "";
      limpiarEstadoInvalido(especialidadSelect);
      limpiarEstadoInvalido(profesionalInput);
    });
  }

  // 3. Menú de acciones principales
  document.querySelectorAll(".action-button[data-panel]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const panelId = btn.getAttribute("data-panel");
      if (panelId) {
        abrirPanel(panelId);
      }
    });
  });

  document.querySelectorAll(".action-button[data-scroll]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const scrollId = btn.getAttribute("data-scroll");
      if (scrollId) {
        const targetElement = document.getElementById(scrollId);
        if (targetElement) {
          targetElement.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }
    });
  });

  // 4. Botones para cerrar paneles
  document.querySelectorAll("[data-close-panel]").forEach((btn) => {
    btn.addEventListener("click", () => {
      cerrarTodosLosPaneles();
    });
  });

  // 5. Botón "Solicitar otro turno" desde la confirmación
  const btnNewAppointment = document.querySelector("[data-new-appointment]");
  if (btnNewAppointment) {
    btnNewAppointment.addEventListener("click", () => {
      confirmacionPanel.hidden = true;
      if (turnoForm) {
        turnoForm.reset();
      }
      if (profesionalInput) {
        profesionalInput.value = "";
      }
      limpiarTodosLosErrores();
      abrirPanel("turno-panel");
    });
  }

  // 6. Botones de acceso a Login Kiosco (Header y Footer) -> Redirigen a /kiosco/
  if (btnKioskTrigger) {
    btnKioskTrigger.addEventListener("click", () => {
      window.location.href = "/kiosco/";
    });
  }

  if (btnFooterKiosk) {
    btnFooterKiosk.addEventListener("click", () => {
      window.location.href = "/kiosco/";
    });
  }

  // 7. ENVÍO DEL FORMULARIO DE SOLICITUD DE TURNO
  if (turnoForm) {
    turnoForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      limpiarMensaje(turnoError);

      const nombreInput = turnoForm.querySelector("input[name='nombre']");
      const dniInput = turnoForm.querySelector("input[name='dni']");
      const telefonoInput = turnoForm.querySelector("input[name='telefono']");
      const fechaEl = turnoForm.querySelector("input[name='fecha']");
      const horaEl =
        turnoForm.querySelector("select[name='hora']") ||
        turnoForm.querySelector("select[name='horario']");

      const nombre = String(nombreInput?.value || "").trim();
      const dni = String(dniInput?.value || "").replace(/\D/g, "");
      const telefono = String(telefonoInput?.value || "").trim();
      const especialidad = String(especialidadSelect?.value || "").trim();
      const profesional = String(profesionalInput?.value || "").trim();
      const fecha = String(fechaEl?.value || "").trim();
      const hora = String(horaEl?.value || "").trim();

      // Limpiar estados visuales previos
      [nombreInput, dniInput, telefonoInput, especialidadSelect, profesionalInput, fechaEl, horaEl].forEach(
        limpiarEstadoInvalido
      );

      // Validaciones obligatorias
      let primerCampoInvalido = null;

      if (!nombre || nombre.length < 3) {
        marcarInvalido(nombreInput);
        if (!primerCampoInvalido) primerCampoInvalido = nombreInput;
      }

      if (!dni || dni.length < 7 || dni.length > 8) {
        marcarInvalido(dniInput);
        if (!primerCampoInvalido) primerCampoInvalido = dniInput;
      }

      if (!telefono) {
        marcarInvalido(telefonoInput);
        if (!primerCampoInvalido) primerCampoInvalido = telefonoInput;
      }

      if (!especialidad) {
        marcarInvalido(especialidadSelect);
        if (!primerCampoInvalido) primerCampoInvalido = especialidadSelect;
      }

      if (!profesional || SPECIALTY_DOCTOR_MAP[especialidad] !== profesional) {
        marcarInvalido(profesionalInput);
        if (!primerCampoInvalido) primerCampoInvalido = profesionalInput;
      }

      const today = new Date().toISOString().split("T")[0];
      if (!fecha || fecha < today) {
        marcarInvalido(fechaEl);
        if (!primerCampoInvalido) primerCampoInvalido = fechaEl;
      }

      if (!hora) {
        marcarInvalido(horaEl);
        if (!primerCampoInvalido) primerCampoInvalido = horaEl;
      }

      if (primerCampoInvalido) {
        if (dni && (dni.length < 7 || dni.length > 8)) {
          mostrarMensaje(turnoError, "Ingresá un DNI válido de 7 u 8 números.");
        } else if (fecha && fecha < today) {
          mostrarMensaje(turnoError, "La fecha del turno debe ser actual o futura.");
        } else if (especialidad && profesional && SPECIALTY_DOCTOR_MAP[especialidad] !== profesional) {
          mostrarMensaje(turnoError, "La especialidad y el profesional seleccionados no coinciden.");
        } else {
          mostrarMensaje(
            turnoError,
            "Revisá los campos marcados. Todos los datos son obligatorios y el DNI debe tener 7 u 8 números."
          );
        }
        primerCampoInvalido.focus();
        return;
      }

      const submitBtn = turnoForm.querySelector("button[type='submit']");
      const textoOriginal = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = "PROCESANDO…";

      // Payload exacto para Code.gs: No enviar email ni estado
      const session = getLocalSession();
      const payload = {
        action: "create",
        token: (session && session.token) || "",
        nombre,
        dni,
        telefono,
        especialidad,
        profesional,
        fecha,
        hora
      };

      try {
        const result = await enviarPeticionAppsScript(payload);

        if (result && result.ok) {
          // Adaptar frontend a la respuesta del backend (sea result.appointment, result.data o campos directos)
          const apptData = result.appointment || result.data || result.turno || result;
          const apptConfirmado = {
            idTurno: apptData.idTurno || apptData.id || result.idTurno || result.id || "-",
            nombre: apptData.nombre || nombre,
            dni: apptData.dni || dni,
            telefono: apptData.telefono || telefono,
            especialidad: apptData.especialidad || especialidad,
            profesional: apptData.profesional || profesional,
            fecha: apptData.fecha || fecha,
            hora: apptData.hora || apptData.horario || hora,
            estado: "Solicitud recibida"
          };

          mostrarConfirmacion(apptConfirmado);
          turnoPanel.hidden = true;
          turnoForm.reset();
          profesionalInput.value = "";
        } else {
          const mensajeError =
            (result && (result.error || result.message)) ||
            "No pudimos procesar la solicitud. Intentá nuevamente.";
          mostrarMensaje(turnoError, mensajeError);
        }
      } catch (err) {
        console.error("Error al registrar turno:", err);
        mostrarMensaje(
          turnoError,
          "No pudimos comunicarnos con la agenda. Intentá nuevamente o llamá a secretaría."
        );
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = textoOriginal;
      }
    });
  }

  // 8. ENVÍO DEL FORMULARIO DE CONSULTA POR DNI
  if (consultaForm) {
    consultaForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      limpiarMensaje(consultaError);
      consultaResultado.innerHTML = "";

      const dniInput = consultaForm.querySelector("input[name='dni']");
      const dni = String(dniInput?.value || "").replace(/\D/g, "");

      limpiarEstadoInvalido(dniInput);

      if (!dni || dni.length < 7 || dni.length > 8) {
        marcarInvalido(dniInput);
        mostrarMensaje(consultaError, "Ingresá un DNI válido de 7 u 8 números.");
        if (dniInput) dniInput.focus();
        return;
      }

      const submitBtn = consultaForm.querySelector("button[type='submit']");
      const textoOriginal = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = "BUSCANDO…";

      const session = getLocalSession();
      const payload = {
        action: "lookup",
        token: (session && session.token) || "",
        dni: dni
      };

      try {
        const result = await enviarPeticionAppsScript(payload);

        // Adaptar a cualquier estructura devuelta por el Code.gs
        let foundAppt = null;
        if (result) {
          if (result.appointment) foundAppt = result.appointment;
          else if (result.data) foundAppt = result.data;
          else if (result.turno) foundAppt = result.turno;
          else if (Array.isArray(result.turnos) && result.turnos.length > 0) foundAppt = result.turnos[0];
          else if (Array.isArray(result.rows) && result.rows.length > 0) foundAppt = result.rows[0];
          else if (result.nombre || result.dni) foundAppt = result;
        }

        if (result && result.ok && result.found !== false && foundAppt) {
          mostrarResultadoConsulta({
            registro: foundAppt.registro || "-",
            idTurno: foundAppt.idTurno || foundAppt.id || "-",
            nombre: foundAppt.nombre || "-",
            dni: foundAppt.dni || dni,
            telefono: foundAppt.telefono || "-",
            especialidad: foundAppt.especialidad || "-",
            profesional: foundAppt.profesional || "-",
            fecha: foundAppt.fecha || "-",
            hora: foundAppt.hora || foundAppt.horario || "-",
            estado: "Solicitud recibida"
          });
        } else {
          consultaResultado.innerHTML = `
            <div class="empty-result" role="status">
              No se encontraron turnos para este DNI.
            </div>
          `;
        }
      } catch (err) {
        console.error("Error al consultar turno:", err);
        mostrarMensaje(
          consultaError,
          "No pudimos comunicarnos con la agenda. Intentá nuevamente o llamá a secretaría."
        );
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = textoOriginal;
      }
    });
  }

  // 9. AUTENTICACIÓN KIOSCO: INICIO DE SESIÓN
  if (kioskLoginForm) {
    kioskLoginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      limpiarMensaje(kioskLoginError);

      const emailInput = kioskLoginForm.querySelector("input[name='email']");
      const passwordInput = kioskLoginForm.querySelector("input[name='password']");

      const email = String(emailInput?.value || "").trim().toLowerCase();
      const password = String(passwordInput?.value || "");

      limpiarEstadoInvalido(emailInput);
      limpiarEstadoInvalido(passwordInput);

      if (!email || !password) {
        if (!email) marcarInvalido(emailInput);
        if (!password) marcarInvalido(passwordInput);
        mostrarMensaje(kioskLoginError, "Por favor completá correo y contraseña.");
        return;
      }

      const submitBtn = kioskLoginForm.querySelector("button[type='submit']");
      const textoOriginal = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = "AUTENTICANDO…";

      try {
        const result = await enviarPeticionAppsScript({
          action: "login",
          email: email,
          password: password
        });

        // El backend devuelve token, email, role directamente (no necesariamente result.user)
        if (result && result.ok && result.token) {
          const userEmail = result.email || (result.user && result.user.email) || email;
          const userRole = result.role || result.rol || (result.user && result.user.rol) || "Kiosco";

          guardarSesionLocal({
            token: result.token,
            email: userEmail,
            rol: userRole,
            expiration: result.expiration || null
          });

          if (kioskUserEmail) {
            kioskUserEmail.textContent = userEmail;
          }
          abrirPanel("kiosk-private-panel");
          kioskLoginForm.reset();
        } else {
          mostrarMensaje(
            kioskLoginError,
            (result && (result.error || result.message)) || "Correo o contraseña incorrectos."
          );
        }
      } catch (err) {
        console.error("Error al autenticar Kiosco:", err);
        mostrarMensaje(
          kioskLoginError,
          "No pudimos conectar con el servidor de autenticación. Intentá nuevamente."
        );
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = textoOriginal;
      }
    });
  }

  // 10. BOTÓN DE CIERRE DE SESIÓN KIOSCO
  if (btnKioskLogout) {
    btnKioskLogout.addEventListener("click", () => {
      cerrarSesionKiosco();
    });
  }

  // 11. KIOSCO: BÚSQUEDA RÁPIDA DE PACIENTE EN SALA
  if (kioskLookupForm) {
    kioskLookupForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      limpiarMensaje(kioskSearchError);
      kioskSearchResult.innerHTML = "";

      const dniInput = document.getElementById("kiosk-search-dni");
      const dni = String(dniInput?.value || "").replace(/\D/g, "");

      if (!dni || dni.length < 7 || dni.length > 8) {
        mostrarMensaje(kioskSearchError, "Ingresá un DNI válido de 7 u 8 números.");
        dniInput?.focus();
        return;
      }

      const submitBtn = document.getElementById("btn-kiosk-search");
      const textoOriginal = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = "Buscando…";

      try {
        const session = getLocalSession();
        const result = await enviarPeticionAppsScript({
          action: "lookup",
          token: (session && session.token) || "",
          dni: dni
        });

        let foundAppt = null;
        if (result) {
          if (result.appointment) foundAppt = result.appointment;
          else if (result.data) foundAppt = result.data;
          else if (result.turno) foundAppt = result.turno;
          else if (Array.isArray(result.turnos) && result.turnos.length > 0) foundAppt = result.turnos[0];
          else if (result.nombre || result.dni) foundAppt = result;
        }

        if (result && result.ok && result.found !== false && foundAppt) {
          renderizarResultadoKiosco(foundAppt);
        } else {
          kioskSearchResult.innerHTML = `
            <div class="empty-result">No se encontraron turnos registrados para el DNI ${escapeHtml(dni)}.</div>
          `;
        }
      } catch (err) {
        console.error("Error en búsqueda Kiosco:", err);
        mostrarMensaje(kioskSearchError, "No pudimos consultar la agenda médica.");
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = textoOriginal;
      }
    });
  }

  // 12. KIOSCO: BOTÓN "NUEVO TURNO KIOSCO"
  if (btnKioskCrearTurno) {
    btnKioskCrearTurno.addEventListener("click", () => {
      abrirPanel("turno-panel");
    });
  }

  // ===================================================================
  // GESTIÓN DE SESIONES Y VALIDACIÓN EN EL SERVIDOR (APPS SCRIPT)
  // ===================================================================

  /**
   * Valida obligatoriamente el token con Google Apps Script antes de dar acceso al panel
   * Reconoce tanto result.authenticated como result.valid
   */
  async function verificarYMostrarPanelKiosco(token) {
    try {
      const result = await enviarPeticionAppsScript({
        action: "verify_session",
        token: token
      });

      const isAuthenticated =
        result && result.ok && (result.authenticated === true || result.valid === true);
      const userRole = (result && (result.role || result.rol || (result.user && result.user.rol))) || "";

      if (isAuthenticated && String(userRole).toLowerCase() === "kiosco") {
        const email =
          result.email || (result.user && result.user.email) || "valentinagalo12@gmail.com";
        if (kioskUserEmail) {
          kioskUserEmail.textContent = email;
        }
        abrirPanel("kiosk-private-panel");
      } else {
        console.warn("Sesión inválida o expirada en el servidor.");
        cerrarSesionKiosco(true);
      }
    } catch (err) {
      console.warn("No se pudo verificar la sesión con Google Apps Script:", err);
      abrirPanel("kiosk-login-panel");
    }
  }

  function cerrarSesionKiosco(porExpiracion = false) {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    if (kioskPrivatePanel) kioskPrivatePanel.hidden = true;
    if (kioskSearchResult) kioskSearchResult.innerHTML = "";
    if (porExpiracion) {
      abrirPanel("kiosk-login-panel");
      mostrarMensaje(kioskLoginError, "Tu sesión expiró. Por favor iniciá sesión nuevamente.");
    } else {
      cerrarTodosLosPaneles();
    }
  }

  function guardarSesionLocal(sessionData) {
    try {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessionData));
    } catch (e) {
      console.warn("No se pudo guardar la sesión en almacenamiento local:", e);
    }
  }

  function getLocalSession() {
    try {
      const raw = localStorage.getItem(SESSION_STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  function renderizarResultadoKiosco(appt) {
    const idTurno = escapeHtml(appt.idTurno || appt.id || "-");
    const dni = escapeHtml(appt.dni || "");
    const nombre = escapeHtml(appt.nombre || "-");
    const telefono = escapeHtml(appt.telefono || "-");
    const especialidad = escapeHtml(appt.especialidad || "-");
    const profesional = escapeHtml(appt.profesional || "-");
    const fecha = formatearFecha(appt.fecha);
    const hora = escapeHtml(appt.hora || appt.horario || "-");

    kioskSearchResult.innerHTML = `
      <div class="result-card">
        <div class="result-header">
          <h3>Paciente: ${nombre}</h3>
          <span class="badge-status">ID: ${idTurno}</span>
        </div>
        <dl class="appointment-detail">
          <div><dt>DNI</dt><dd>${dni}</dd></div>
          <div><dt>Teléfono</dt><dd>${telefono}</dd></div>
          <div><dt>Especialidad</dt><dd>${especialidad}</dd></div>
          <div><dt>Profesional</dt><dd>${profesional}</dd></div>
          <div><dt>Fecha</dt><dd>${fecha}</dd></div>
          <div><dt>Horario</dt><dd>${hora} hs.</dd></div>
        </dl>
      </div>
    `;
  }

  // ===================================================================
  // COMUNICACIÓN HTTP DIRECTA CON GOOGLE APPS SCRIPT
  // ===================================================================

  async function enviarPeticionAppsScript(payload) {
    const response = await fetch(APPS_SCRIPT_URL, {
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
  // RENDERIZADO VISUAL DE CONFIRMACIÓN Y RESULTADOS
  // ===================================================================

  function mostrarConfirmacion(appt) {
    confirmacionDetalle.innerHTML = `
      <div><dt>Paciente</dt><dd>${escapeHtml(appt.nombre)}</dd></div>
      <div><dt>DNI</dt><dd>${escapeHtml(appt.dni)}</dd></div>
      <div><dt>Especialidad</dt><dd>${escapeHtml(appt.especialidad)}</dd></div>
      <div><dt>Profesional</dt><dd>${escapeHtml(appt.profesional)}</dd></div>
      <div><dt>Fecha</dt><dd>${formatearFecha(appt.fecha)}</dd></div>
      <div><dt>Horario</dt><dd>${escapeHtml(appt.hora || appt.horario)} hs.</dd></div>
      <div><dt>Estado</dt><dd>${escapeHtml(appt.estado || "Solicitud recibida")}</dd></div>
    `;
    confirmacionPanel.hidden = false;
    confirmacionPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    confirmacionPanel.focus();
  }

  function mostrarResultadoConsulta(appt) {
    consultaResultado.innerHTML = `
      <div class="result-card" role="region" aria-label="Turno encontrado">
        <div class="result-header">
          <h3>Turno encontrado</h3>
          <span class="badge-status">${escapeHtml(appt.estado || "Solicitud recibida")}</span>
        </div>
        <dl class="appointment-detail">
          <div><dt>Paciente</dt><dd>${escapeHtml(appt.nombre)}</dd></div>
          <div><dt>DNI</dt><dd>${escapeHtml(appt.dni)}</dd></div>
          <div><dt>Especialidad</dt><dd>${escapeHtml(appt.especialidad)}</dd></div>
          <div><dt>Profesional</dt><dd>${escapeHtml(appt.profesional)}</dd></div>
          <div><dt>Fecha</dt><dd>${formatearFecha(appt.fecha)}</dd></div>
          <div><dt>Horario</dt><dd>${escapeHtml(appt.hora || appt.horario)} hs.</dd></div>
          <div><dt>Estado</dt><dd>${escapeHtml(appt.estado || "Solicitud recibida")}</dd></div>
        </dl>
      </div>
    `;
    consultaResultado.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // ===================================================================
  // FUNCIONES AUXILIARES DE UI Y VALIDACIÓN
  // ===================================================================

  function abrirPanel(id) {
    cerrarTodosLosPaneles();
    limpiarTodosLosErrores();

    const target = document.getElementById(id);
    if (target) {
      target.hidden = false;
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      const firstInput = target.querySelector("input:not([readonly]), select");
      if (firstInput) {
        setTimeout(() => firstInput.focus(), 150);
      }
    }
  }

  function cerrarTodosLosPaneles() {
    if (turnoPanel) turnoPanel.hidden = true;
    if (consultaPanel) consultaPanel.hidden = true;
    if (confirmacionPanel) confirmacionPanel.hidden = true;
    if (kioskLoginPanel) kioskLoginPanel.hidden = true;
    if (kioskPrivatePanel) kioskPrivatePanel.hidden = true;
    limpiarTodosLosErrores();
  }

  function marcarInvalido(el) {
    if (el) {
      el.setAttribute("aria-invalid", "true");
    }
  }

  function limpiarEstadoInvalido(el) {
    if (el) {
      el.removeAttribute("aria-invalid");
    }
  }

  function mostrarMensaje(container, texto) {
    if (!container) return;
    container.textContent = texto;
    container.className = "form-message error-message";
    container.hidden = false;
  }

  function limpiarMensaje(container) {
    if (!container) return;
    container.hidden = true;
    container.textContent = "";
  }

  function limpiarTodosLosErrores() {
    limpiarMensaje(turnoError);
    limpiarMensaje(consultaError);
    limpiarMensaje(kioskLoginError);
    limpiarMensaje(kioskSearchError);

    document.querySelectorAll("[aria-invalid='true']").forEach(limpiarEstadoInvalido);
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

  // En index.html la sesión y vista de Kiosco se gestiona de forma aislada en kiosco.html
});
