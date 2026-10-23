/**
 * ===================================================================
 * UMSA - CENTRO MÉDICO ("APOSTÁ A LA VIDA")
 * Lógica interactiva, validaciones, gestión de turnos, chatbot y sistema Kiosco.
 * Versión Django - Fase 1 (Frontend e interactividad local sin backend externo)
 * ===================================================================
 */

document.addEventListener("DOMContentLoaded", () => {
  const SESSION_STORAGE_KEY = "umsa_kiosk_session";
  const TURNOS_STORAGE_KEY = "umsa_turnos_locales";

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

  // Chatbot
  const chatbotToggle = document.getElementById("chatbot-toggle");
  const chatbotWindow = document.getElementById("chatbot-window");
  const chatbotClose = document.getElementById("chatbot-close");
  const chatbotMessages = document.getElementById("chatbot-messages");

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

  // 6. Botones de acceso a Login Kiosco (Header y Footer)
  if (btnKioskTrigger) {
    btnKioskTrigger.addEventListener("click", (e) => {
      e.preventDefault();
      gestionarAccesoKiosco();
    });
  }

  if (btnFooterKiosk) {
    btnFooterKiosk.addEventListener("click", (e) => {
      e.preventDefault();
      gestionarAccesoKiosco();
    });
  }

  function gestionarAccesoKiosco() {
    const session = getLocalSession();
    if (session && session.email) {
      mostrarPanelKiosco(session.email);
    } else {
      abrirPanel("kiosk-login-panel");
    }
  }

  // 7. ENVÍO DEL FORMULARIO DE SOLICITUD DE TURNO (Simulación local reactiva)
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

      [nombreInput, dniInput, telefonoInput, especialidadSelect, profesionalInput, fechaEl, horaEl]
        .forEach(limpiarEstadoInvalido);

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
        } else if (
          especialidad &&
          profesional &&
          SPECIALTY_DOCTOR_MAP[especialidad] !== profesional
        ) {
          mostrarMensaje(
            turnoError,
            "La especialidad y el profesional seleccionados no coinciden."
          );
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

      try {
        const csrfToken = getCsrfToken();
        const headers = {
          "X-Requested-With": "XMLHttpRequest"
        };
        if (csrfToken) {
          headers["X-CSRFToken"] = csrfToken;
        }

        const response = await fetch(turnoForm.action, {
          method: "POST",
          body: new FormData(turnoForm),
          headers: headers
        });

        if (!response.ok) {
          throw new Error("No se pudo guardar el turno.");
        }

        const data = await response.json();

        const apptConfirmado = {
          idTurno: data.id_turno,
          nombre,
          dni,
          telefono,
          especialidad,
          profesional,
          fecha,
          hora,
          estado: "Solicitud recibida"
        };

        guardarTurnoLocal(apptConfirmado);
        mostrarConfirmacion(apptConfirmado);

        turnoPanel.hidden = true;
        turnoForm.reset();

        if (profesionalInput) {
          profesionalInput.value = "";
        }

      } catch (error) {
        console.error("Error al guardar el turno:", error);

        mostrarMensaje(
          turnoError,
          "No se pudo registrar el turno. Intentá nuevamente."
        );
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = textoOriginal;
      }
    });
  }
  // 8. ENVÍO DEL FORMULARIO DE CONSULTA POR DNI
  if (consultaForm) {
    consultaForm.addEventListener("submit", (e) => {
      e.preventDefault();
      limpiarMensaje(consultaError);
      consultaResultado.innerHTML = "";

      const dniInput = consultaForm.querySelector("input[name='dni']");
      const dni = String(dniInput?.value || "").replace(/\D/g, "");

      limpiarEstadoInvalido(dniInput);

      if (!dni || dni.length < 7 || dni.length > 8) {
        marcarInvalido(dniInput);
        mostrarMensaje(consultaError, "Ingresá un DNI válido de 7 u 8 números.");
        dniInput?.focus();
        return;
      }

      const searchBtn = consultaForm.querySelector("button[type='submit']");
      const textoOriginal = searchBtn.textContent;
      searchBtn.disabled = true;
      searchBtn.textContent = "BUSCANDO…";

      setTimeout(() => {
        searchBtn.disabled = false;
        searchBtn.textContent = textoOriginal;

        const turnoEncontrado = buscarTurnoLocalPorDni(dni) || {
          idTurno: `UMSA-${Math.floor(100000 + Math.random() * 900000)}`,
          nombre: "Paciente Ejemplo",
          dni: dni,
          telefono: "2325 400000",
          especialidad: "Clínica Médica",
          profesional: "Dr. Lecouna",
          fecha: new Date().toISOString().split("T")[0],
          hora: "10:00",
          estado: "Solicitud recibida"
        };

        mostrarResultadoConsulta(turnoEncontrado);
      }, 350);
    });
  }

  // 9. AUTENTICACIÓN KIOSCO (Login interactivo local)
  if (kioskLoginForm) {
    kioskLoginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      limpiarMensaje(kioskLoginError);

      const emailInput = document.getElementById("kiosk-email");
      const passwordInput = document.getElementById("kiosk-password");

      const email = String(emailInput?.value || "").trim();
      const password = String(passwordInput?.value || "").trim();

      limpiarEstadoInvalido(emailInput);
      limpiarEstadoInvalido(passwordInput);

      if (!email || !email.includes("@")) {
        marcarInvalido(emailInput);
        mostrarMensaje(kioskLoginError, "Ingresá un correo electrónico válido.");
        emailInput?.focus();
        return;
      }

      if (!password) {
        marcarInvalido(passwordInput);
        mostrarMensaje(kioskLoginError, "Ingresá tu contraseña de operador.");
        passwordInput?.focus();
        return;
      }

      const loginBtn = document.getElementById("btn-login-submit");
      loginBtn.disabled = true;
      loginBtn.textContent = "VERIFICANDO…";

      setTimeout(() => {
        loginBtn.disabled = false;
        loginBtn.textContent = "INICIAR SESIÓN";

        // Guardar sesión local
        const session = {
          email: email,
          token: "kiosk-demo-token-" + Date.now(),
          timestamp: Date.now()
        };
        localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));

        kioskLoginForm.reset();
        mostrarPanelKiosco(email);
      }, 400);
    });
  }

  // 10. CIERRE DE SESIÓN KIOSCO
  if (btnKioskLogout) {
    btnKioskLogout.addEventListener("click", () => {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      cerrarTodosLosPaneles();
    });
  }

  // 11. BÚSQUEDA RÁPIDA EN SALA DENTRO DEL PANEL KIOSCO
  if (kioskLookupForm) {
    kioskLookupForm.addEventListener("submit", (e) => {
      e.preventDefault();
      limpiarMensaje(kioskSearchError);
      kioskSearchResult.innerHTML = "";

      const dniInput = document.getElementById("kiosk-search-dni");
      const dni = String(dniInput?.value || "").replace(/\D/g, "");

      limpiarEstadoInvalido(dniInput);

      if (!dni || dni.length < 7 || dni.length > 8) {
        marcarInvalido(dniInput);
        mostrarMensaje(kioskSearchError, "Ingresá un DNI válido de 7 u 8 números.");
        dniInput?.focus();
        return;
      }

      const searchBtn = document.getElementById("btn-kiosk-search");
      searchBtn.disabled = true;
      searchBtn.textContent = "Buscando…";

      setTimeout(() => {
        searchBtn.disabled = false;
        searchBtn.textContent = "Consultar";

        const turnoEncontrado = buscarTurnoLocalPorDni(dni) || {
          idTurno: `UMSA-${Math.floor(100000 + Math.random() * 900000)}`,
          nombre: "Paciente en Sala",
          dni: dni,
          telefono: "2325 400000",
          especialidad: "Clínica Médica",
          profesional: "Dr. Lecouna",
          fecha: new Date().toISOString().split("T")[0],
          hora: "09:00",
          estado: "Solicitud recibida"
        };

        renderKioskSearchResult(turnoEncontrado);
      }, 300);
    });
  }

  function renderKioskSearchResult(appt) {
    kioskSearchResult.innerHTML = `
      <div class="result-card">
        <div class="result-header">
          <strong>${escapeHtml(appt.nombre)} (DNI: ${escapeHtml(appt.dni)})</strong>
          <span class="badge-status" id="kiosk-status-badge">${escapeHtml(appt.estado)}</span>
        </div>
        <dl class="appointment-detail">
          <div><dt>Especialidad</dt><dd>${escapeHtml(appt.especialidad)}</dd></div>
          <div><dt>Profesional</dt><dd>${escapeHtml(appt.profesional)}</dd></div>
          <div><dt>Horario</dt><dd>${escapeHtml(appt.hora)} hs.</dd></div>
        </dl>
        <div style="margin-top: 1rem;">
          <button type="button" class="submit-button" id="btn-marcar-presente" style="font-size: 0.85rem; padding: 0.5rem 1rem;">
            Marcar presente en sala
          </button>
        </div>
      </div>
    `;

    const btnMarcar = document.getElementById("btn-marcar-presente");
    if (btnMarcar) {
      btnMarcar.addEventListener("click", () => {
        const badge = document.getElementById("kiosk-status-badge");
        if (badge) {
          badge.textContent = "Presente en sala";
          badge.style.background = "#e9f5ef";
          badge.style.color = "#176b4d";
        }
        btnMarcar.disabled = true;
        btnMarcar.textContent = "✓ Presente confirmado";
      });
    }
  }

  if (btnKioskCrearTurno) {
    btnKioskCrearTurno.addEventListener("click", () => {
      abrirPanel("turno-panel");
    });
  }

  // ===================================================================
  // CHATBOT UMSA
  // ===================================================================
  if (chatbotToggle && chatbotWindow) {
    chatbotToggle.addEventListener("click", () => {
      chatbotWindow.hidden = !chatbotWindow.hidden;
    });
  }

  if (chatbotClose && chatbotWindow) {
    chatbotClose.addEventListener("click", () => {
      chatbotWindow.hidden = true;
    });
  }

  const chatbotResponses = {
    turno:
      'Para solicitar un turno, seleccioná "Solicitar turno" y completá tus datos, especialidad, profesional, fecha y horario.',
    consulta:
      'Para consultar un turno, seleccioná "Consultar turno" e ingresá tu DNI.',
    especialidades:
      'Actualmente contamos con Clínica Médica, Odontología, Reumatología y Neurología.',
    profesionales:
      'Nuestro equipo incluye profesionales de Clínica Médica, Odontología, Reumatología y Neurología.',
    faq:
      'Podés encontrar respuestas sobre turnos, consultas, documentación y especialidades en nuestra sección de Preguntas frecuentes.',
    contacto:
      '📍 Estamos en San Martín 711, San Andrés de Giles. 📞 Teléfono: 2325 442727. Secretaría: lunes a viernes de 7:00 a 20:00 hs.',
    nosotros:
      '🏥 UMSA Centro Médico es un centro de emergencias médicas privado que brinda atención y asistencia médica a la comunidad de San Andrés de Giles. Nuestro objetivo es ofrecer una atención cercana, profesional y responsable, acompañando a cada paciente en el cuidado de su salud. ❤️ APOSTÁ A LA VIDA.'
  };

  document.querySelectorAll("[data-chat-option]").forEach((button) => {
    button.addEventListener("click", () => {
      const option = button.dataset.chatOption;
      const response = chatbotResponses[option];

      if (!response || !chatbotMessages) return;

      const userMessage = document.createElement("div");
      userMessage.className = "chatbot-message user";
      userMessage.textContent = button.textContent;
      chatbotMessages.appendChild(userMessage);

      const botMessage = document.createElement("div");
      botMessage.className = "chatbot-message bot";
      botMessage.textContent = response;
      chatbotMessages.appendChild(botMessage);

      chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    });
  });

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

  function mostrarPanelKiosco(email) {
    cerrarTodosLosPaneles();
    if (kioskUserEmail) {
      kioskUserEmail.textContent = email || "operador@kiosco";
    }
    if (kioskPrivatePanel) {
      kioskPrivatePanel.hidden = false;
      kioskPrivatePanel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
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

  function getLocalSession() {
    try {
      const data = localStorage.getItem(SESSION_STORAGE_KEY);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      return null;
    }
  }

  function guardarTurnoLocal(appt) {
    try {
      const list = JSON.parse(localStorage.getItem(TURNOS_STORAGE_KEY) || "[]");
      list.unshift(appt);
      localStorage.setItem(TURNOS_STORAGE_KEY, JSON.stringify(list));
    } catch (e) { }
  }

  function buscarTurnoLocalPorDni(dni) {
    try {
      const list = JSON.parse(localStorage.getItem(TURNOS_STORAGE_KEY) || "[]");
      return list.find((item) => String(item.dni) === String(dni)) || null;
    } catch (e) {
      return null;
    }
  }

  function getCsrfToken() {
    const input = turnoForm ? turnoForm.querySelector("input[name='csrfmiddlewaretoken']") : document.querySelector("input[name='csrfmiddlewaretoken']");
    if (input && input.value) {
      return input.value;
    }
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith("csrftoken=")) {
        return decodeURIComponent(cookie.substring("csrftoken=".length));
      }
    }
    return "";
  }

  // Verificación de sesión al cargar la página
  const savedSession = getLocalSession();
  if (savedSession && savedSession.email) {
    if (kioskUserEmail) {
      kioskUserEmail.textContent = savedSession.email;
    }
  }
});
