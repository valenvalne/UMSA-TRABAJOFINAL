/**
 * ===================================================================
 * UMSA - CENTRO MÉDICO ("APOSTÁ A LA VIDA")
 * Lógica interactiva del widget "¡Tu opinión nos importa!" (opiniones.js)
 * ===================================================================
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elementos principales del widget
  const widget = document.getElementById("opiniones-widget");
  const toggleBtn = document.getElementById("opiniones-toggle");
  const windowEl = document.getElementById("opiniones-window");
  const closeBtn = document.getElementById("opiniones-close");

  // Formulario y campos
  const form = document.getElementById("opiniones-form");
  const nombreInput = document.getElementById("opinion-nombre");
  const comentarioInput = document.getElementById("opinion-comentario");
  const clasificacionInput = document.getElementById("opinion-clasificacion");
  const starsContainer = document.getElementById("rating-stars");
  const starButtons = starsContainer ? Array.from(starsContainer.querySelectorAll(".star-btn")) : [];
  const ratingHint = document.getElementById("rating-hint");
  const errorEl = document.getElementById("opiniones-error");

  // Estado de éxito y botón de envío
  const successEl = document.getElementById("opiniones-success");
  const resetBtn = document.getElementById("btn-nueva-opinion");
  const submitBtn = document.getElementById("btn-enviar-opinion");

  // Conexión directa a Google Apps Script para opiniones
  const OPINIONES_APPS_SCRIPT_URL =
    "https://script.google.com/macros/s/AKfycbxBqgw4D9F3lqxA_PeSjGnlIjULmDB33jFz5O_ARpJW93Ovj4gv57uHTxQruUvI56EF/exec";

  // Valor actual de calificación (1 a 5, inicial 0)
  let currentRating = 0;

  const RATING_TEXTS = {
    1: "1 estrella · Muy mala",
    2: "2 estrellas · Regular",
    3: "3 estrellas · Buena",
    4: "4 estrellas · Muy buena",
    5: "5 estrellas · ¡Excelente!"
  };

  // ===================================================================
  // 1. APERTURA Y CIERRE DE LA VENTANA FLOTANTE
  // ===================================================================

  function abrirVentana() {
    if (!windowEl) return;
    windowEl.hidden = false;
    if (toggleBtn) toggleBtn.setAttribute("aria-expanded", "true");
    setTimeout(() => {
      if (nombreInput) nombreInput.focus();
    }, 100);
  }

  function cerrarVentana() {
    if (!windowEl) return;
    windowEl.hidden = true;
    if (toggleBtn) {
      toggleBtn.setAttribute("aria-expanded", "false");
      toggleBtn.focus();
    }
  }

  function alternarVentana() {
    if (!windowEl) return;
    if (windowEl.hidden) {
      abrirVentana();
    } else {
      cerrarVentana();
    }
  }

  if (toggleBtn) {
    toggleBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      alternarVentana();
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      cerrarVentana();
    });
  }

  // Cerrar con tecla Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && windowEl && !windowEl.hidden) {
      cerrarVentana();
    }
  });

  // Cerrar al hacer clic fuera del widget
  document.addEventListener("click", (e) => {
    if (windowEl && !windowEl.hidden && widget && !widget.contains(e.target)) {
      cerrarVentana();
    }
  });

  // Evitar que los clics dentro de la ventana se propaguen al documento
  if (windowEl) {
    windowEl.addEventListener("click", (e) => {
      e.stopPropagation();
    });
  }

  // ===================================================================
  // 2. SISTEMA INTERACTIVO DE 5 ESTRELLAS
  // ===================================================================

  function iluminarEstrellas(cantidad, clase = "is-active") {
    starButtons.forEach((btn, index) => {
      if (index < cantidad) {
        btn.classList.add(clase);
      } else {
        btn.classList.remove(clase);
      }
    });
  }

  function limpiarHover() {
    starButtons.forEach((btn) => btn.classList.remove("is-hover"));
    iluminarEstrellas(currentRating, "is-active");
  }

  function actualizarTextoCalificacion(rating) {
    if (!ratingHint) return;
    if (rating > 0 && RATING_TEXTS[rating]) {
      ratingHint.textContent = RATING_TEXTS[rating];
      ratingHint.classList.add("has-value");
    } else {
      ratingHint.textContent = "Tocá las estrellas para calificar";
      ratingHint.classList.remove("has-value");
    }
  }

  function seleccionarCalificacion(rating) {
    currentRating = rating;
    if (clasificacionInput) {
      clasificacionInput.value = rating > 0 ? String(rating) : "";
    }
    iluminarEstrellas(currentRating, "is-active");
    actualizarTextoCalificacion(currentRating);
    limpiarMensajeError();
  }

  starButtons.forEach((btn) => {
    const ratingValue = parseInt(btn.getAttribute("data-value") || "0", 10);

    // Hover con mouse
    btn.addEventListener("mouseenter", () => {
      iluminarEstrellas(ratingValue, "is-hover");
      actualizarTextoCalificacion(ratingValue);
    });

    // Clic con mouse o toque
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      seleccionarCalificacion(ratingValue);
    });

    // Accesibilidad por teclado (Flechas Izquierda / Derecha)
    btn.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowUp") {
        e.preventDefault();
        const next = Math.min(starButtons.length, ratingValue + 1);
        seleccionarCalificacion(next);
        starButtons[next - 1]?.focus();
      } else if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
        e.preventDefault();
        const prev = Math.max(1, ratingValue - 1);
        seleccionarCalificacion(prev);
        starButtons[prev - 1]?.focus();
      }
    });
  });

  if (starsContainer) {
    starsContainer.addEventListener("mouseleave", () => {
      limpiarHover();
      actualizarTextoCalificacion(currentRating);
    });
  }

  // ===================================================================
  // 3. VALIDACIÓN Y ENVÍO DEL FORMULARIO
  // ===================================================================

  function mostrarMensajeError(mensaje) {
    if (!errorEl) return;
    errorEl.textContent = mensaje;
    errorEl.hidden = false;
  }

  function limpiarMensajeError() {
    if (!errorEl) return;
    errorEl.hidden = true;
    errorEl.textContent = "";
    if (nombreInput) nombreInput.removeAttribute("aria-invalid");
    if (comentarioInput) comentarioInput.removeAttribute("aria-invalid");
  }

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      limpiarMensajeError();

      const nombre = String(nombreInput?.value || "").trim();
      const comentario = String(comentarioInput?.value || "").trim();

      // Validaciones obligatorias
      if (!nombre || nombre.length < 2) {
        if (nombreInput) {
          nombreInput.setAttribute("aria-invalid", "true");
          nombreInput.focus();
        }
        mostrarMensajeError("Por favor ingresá tu nombre y apellido.");
        return;
      }

      if (currentRating === 0) {
        mostrarMensajeError("Por favor seleccioná una clasificación con las estrellas.");
        if (starButtons[0]) starButtons[0].focus();
        return;
      }

      if (!comentario || comentario.length < 4) {
        if (comentarioInput) {
          comentarioInput.setAttribute("aria-invalid", "true");
          comentarioInput.focus();
        }
        mostrarMensajeError("Por favor escribí tu comentario antes de enviar.");
        return;
      }

      // Deshabilitar botón durante el envío para evitar envíos duplicados
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "ENVIANDO...";
      }

      try {
        const payload = {
          action: "guardar_opinion",
          nombre: nombre,
          clasificacion: currentRating,
          comentario: comentario
        };

        const response = await fetch(OPINIONES_APPS_SCRIPT_URL, {
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

        if (data && data.ok) {
          // Mostrar mensaje de agradecimiento
          form.hidden = true;
          if (successEl) successEl.hidden = false;
        } else {
          // Error devuelto por Apps Script
          const mensajeError =
            (data && data.mensaje) ||
            "No se pudo guardar la opinión. Por favor, intentá nuevamente.";
          mostrarMensajeError(mensajeError);
        }
      } catch (error) {
        console.error("Error al guardar la opinión:", error);
        mostrarMensajeError(
          "Ocurrió un error al enviar tu opinión. Por favor, intentá nuevamente."
        );
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "ENVIAR OPINIÓN";
        }
      }
    });
  }

  // Reiniciar para dejar otro comentario
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      if (form) {
        form.reset();
        form.hidden = false;
      }
      if (successEl) successEl.hidden = true;
      currentRating = 0;
      limpiarHover();
      actualizarTextoCalificacion(0);
      limpiarMensajeError();
      if (nombreInput) nombreInput.focus();
    });
  }
});
