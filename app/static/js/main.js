/**
 * UMSA IA · Panel Administrativo Inteligente
 * Lógica Completa de Frontend e Integraciones
 */

document.addEventListener("DOMContentLoaded", () => {

  // =========================================================================
  // 1. UTILIDADES Y CSRF
  // =========================================================================
  function getCsrf() {
    const el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function formatCurrency(num) {
    num = Number(num) || 0;
    return "$ " + num.toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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

  function renderSimpleMarkdown(text) {
    if (!text) return "";
    let safe = escapeHtml(text);
    // Negrita
    safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Código inline
    safe = safe.replace(/`(.*?)`/g, "<code>$1</code>");
    // Bloques de código
    safe = safe.replace(/```([\s\S]*?)```/g, "<pre><code>$1</code></pre>");
    // Saltos de línea
    safe = safe.replace(/\n/g, "<br>");
    return safe;
  }

  // =========================================================================
  // 2. NAVEGACIÓN POR SIDEBAR Y TABS
  // =========================================================================
  const sidebarLinks = document.querySelectorAll(".sidebar-link");
  const viewPanes = document.querySelectorAll(".view-pane");
  const topSectionName = document.getElementById("topSectionName");
  const sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
  const appSidebar = document.getElementById("appSidebar");

  const tabTitles = {
    "tab-dashboard": "Inicio",
    "tab-inventario": "Inventario de Insumos",
    "tab-presupuestos": "Presupuestos Oficiales",
    "tab-historial-presupuestos": "Historial de Presupuestos",
    "tab-pagos": "Medios de Pago y Cobranzas",
    "tab-chat": "Asistente UMSA",
    "tab-archivos": "Archivos",
    "tab-memoria": "Memoria",
    "tab-historial": "Historial",
    "tab-modulos": "Módulos",
    "tab-indice": "Índice",
    "tab-turnos": "Turnos & Médicos",
    "tab-umsa": "Conexión",
    "tab-config": "Configuración",
  };

  function switchTab(targetId) {
    sidebarLinks.forEach(l => l.classList.remove("active"));
    viewPanes.forEach(p => p.classList.remove("active"));

    const activeLink = document.querySelector(`.sidebar-link[data-tab="${targetId}"]`);
    if (activeLink) activeLink.classList.add("active");

    const targetPane = document.getElementById(targetId);
    if (targetPane) targetPane.classList.add("active");

    if (topSectionName && tabTitles[targetId]) {
      topSectionName.textContent = tabTitles[targetId];
    }

    // Cerrar sidebar en móviles
    if (appSidebar) appSidebar.classList.remove("open");

    // Acciones automáticas según pestaña
    if (targetId === "tab-archivos") {
      refreshFilesList();
    } else if (targetId === "tab-inventario") {
      refreshInventarioList();
    } else if (targetId === "tab-memoria") {
      loadMemory();
    } else if (targetId === "tab-historial") {
      loadHistory();
    } else if (targetId === "tab-modulos") {
      loadModules();
    } else if (targetId === "tab-indice") {
      loadIndex();
    } else if (targetId === "tab-presupuestos") {
      refreshPresupuestosList();
    } else if (targetId === "tab-historial-presupuestos") {
      loadHistorialPresupuestos();
    } else if (targetId === "tab-dashboard") {
      refreshDashboardMetrics();
    } else if (targetId === "tab-pagos") {
      refreshPagosSection();
    }
  }

  sidebarLinks.forEach(link => {
    link.addEventListener("click", () => {
      const targetId = link.getAttribute("data-tab");
      if (targetId) switchTab(targetId);
    });
  });

  if (sidebarToggleBtn && appSidebar) {
    sidebarToggleBtn.addEventListener("click", () => {
      appSidebar.classList.toggle("open");
    });
  }

  // Flujo directo de presupuesto en Asistente
  function startBudgetFlow() {
    switchTab("tab-chat");
    if (chatInput) {
      chatInput.value = "Quiero hacer un presupuesto";
      if (chatForm) {
        chatForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
      }
    }
  }

  // Botones principales del Dashboard (Acciones Rápidas)
  const dashQuickNewBudget = document.getElementById("dashQuickNewBudget");
  const dashQuickViewInventory = document.getElementById("dashQuickViewInventory");
  const dashQuickSearch = document.getElementById("dashQuickSearch");
  const dashQuickOpenAssistant = document.getElementById("dashQuickOpenAssistant");
  const dashQuickPayments = document.getElementById("dashQuickPayments");

  if (dashQuickNewBudget) dashQuickNewBudget.onclick = startBudgetFlow;
  if (dashQuickViewInventory) dashQuickViewInventory.onclick = () => switchTab("tab-inventario");
  if (dashQuickSearch) {
    dashQuickSearch.onclick = () => {
      const gInput = document.getElementById("globalSearchInput");
      if (gInput) {
        gInput.focus();
        gInput.select();
      }
    };
  }
  if (dashQuickOpenAssistant) dashQuickOpenAssistant.onclick = () => switchTab("tab-chat");
  if (dashQuickPayments) dashQuickPayments.onclick = () => switchTab("tab-pagos");

  const heroStartBudgetBtn = document.getElementById("heroStartBudgetBtn");
  const dashCardStartBudgetBtn = document.getElementById("dashCardStartBudgetBtn");
  const dashCardViewInventoryBtn = document.getElementById("dashCardViewInventoryBtn");
  const dashCardOpenAssistantBtn = document.getElementById("dashCardOpenAssistantBtn");

  if (heroStartBudgetBtn) heroStartBudgetBtn.onclick = startBudgetFlow;
  if (dashCardStartBudgetBtn) dashCardStartBudgetBtn.onclick = startBudgetFlow;
  if (dashCardViewInventoryBtn) dashCardViewInventoryBtn.onclick = () => switchTab("tab-inventario");
  if (dashCardOpenAssistantBtn) dashCardOpenAssistantBtn.onclick = () => switchTab("tab-chat");

  document.querySelectorAll(".btn-quick-budget").forEach(btn => {
    btn.onclick = startBudgetFlow;
  });

  // Accesos preservados internamente
  const dashStartChatBtn = document.getElementById("dashStartChatBtn");
  const dashViewFilesBtn = document.getElementById("dashViewFilesBtn");
  const dashNewModuleBtn = document.getElementById("dashNewModuleBtn");
  const dashNewPresupuestoBtn = document.getElementById("dashNewPresupuestoBtn");

  if (dashStartChatBtn) dashStartChatBtn.onclick = () => switchTab("tab-chat");
  if (dashViewFilesBtn) dashViewFilesBtn.onclick = () => switchTab("tab-archivos");
  if (dashNewPresupuestoBtn) dashNewPresupuestoBtn.onclick = () => switchTab("tab-presupuestos");
  if (dashNewModuleBtn) {
    dashNewModuleBtn.onclick = () => {
      openFolderModal();
    };
  }

  // Refrescar Métricas del Dashboard (KPIs reales)
  async function refreshDashboardMetrics() {
    try {
      const resp = await fetch("/api/dashboard/metrics/");
      const data = await resp.json();
      if (data.ok && data.metrics) {
        const m = data.metrics;
        const kpiHoy = document.getElementById("dashKpiHoy");
        const kpiPend = document.getElementById("dashKpiPendientes");
        const kpiProd = document.getElementById("dashKpiProductos");
        const kpiTotal = document.getElementById("dashKpiTotal");
        if (kpiHoy) kpiHoy.textContent = m.presupuestos_hoy;
        if (kpiPend) kpiPend.textContent = m.presupuestos_pendientes;
        if (kpiProd) kpiProd.textContent = m.productos_disponibles;
        if (kpiTotal) kpiTotal.textContent = m.tiene_presupuestos ? m.total_presupuestado_formateado : "0";
      }
    } catch (e) {
      console.error("Error al refrescar métricas del dashboard:", e);
    }
  }

  // =========================================================================
  // 3. SINCRONIZACIÓN GLOBAL DE MÓDULO
  // =========================================================================
  const globalModuleSelect = document.getElementById("globalModuleSelect");
  const chatModuleSelect = document.getElementById("chatModuleSelect");
  const moduleFilterSelect = document.getElementById("moduleFilterSelect");
  const memoryModuleSelect = document.getElementById("memoryModuleSelect");
  const historyModuleSelect = document.getElementById("historyModuleSelect");
  const indexModuleSelect = document.getElementById("indexModuleSelect");
  const newFileModuleSelect = document.getElementById("newFileModuleSelect");

  function syncAllModuleSelects(val) {
    const selects = [
      globalModuleSelect,
      chatModuleSelect,
      moduleFilterSelect,
      memoryModuleSelect,
      historyModuleSelect,
      indexModuleSelect,
      newFileModuleSelect
    ];
    selects.forEach(s => {
      if (s) s.value = val;
    });
  }

  if (globalModuleSelect) {
    globalModuleSelect.addEventListener("change", () => {
      const val = globalModuleSelect.value;
      syncAllModuleSelects(val);
      refreshFilesList();
      loadMemory();
      loadHistory();
      loadIndex();
    });
  }

  if (chatModuleSelect) {
    chatModuleSelect.addEventListener("change", () => {
      syncAllModuleSelects(chatModuleSelect.value);
    });
  }

  // =========================================================================
  // 4. ASISTENTE IA (CHAT + TOOL CALLING REAL)
  // =========================================================================
  const chatForm = document.getElementById("chatForm");
  const chatInput = document.getElementById("chatInput");
  const chatMessages = document.getElementById("chatMessages");
  const chatSendBtn = document.getElementById("chatSendBtn");
  const clearChatBtn = document.getElementById("clearChatBtn");

  // Botones de sugerencias rápidas
  document.querySelectorAll(".quick-prompt-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-prompt");
      if (prompt && chatInput) {
        chatInput.value = prompt;
        chatInput.focus();
      }
    });
  });

  if (clearChatBtn) {
    clearChatBtn.addEventListener("click", () => {
      chatMessages.innerHTML = `
        <div class="message-bubble assistant">
          <div class="bubble-header">
            <span class="bubble-author">🤖 Asistente Claude</span>
            <span class="bubble-tag tag-system">SISTEMA</span>
          </div>
          <div class="bubble-body">
            <p>Conversación reiniciada. ¿En qué puedo asistirte ahora?</p>
          </div>
        </div>
      `;
    });
  }

  function appendChatMessage(role, text, toolRecords = []) {
    const bubble = document.createElement("div");
    bubble.className = `message-bubble ${role}`;

    let headerHtml = "";
    if (role === "user") {
      headerHtml = `
        <div class="bubble-header">
          <span class="bubble-author">👤 Administradora UMSA</span>
          <span class="bubble-tag tag-system">USUARIO</span>
        </div>
      `;
    } else {
      headerHtml = `
        <div class="bubble-header">
          <span class="bubble-author">🤖 Asistente UMSA</span>
          <span class="bubble-tag tag-system">ASISTENTE</span>
        </div>
      `;
    }

    bubble.innerHTML = `
      ${headerHtml}
      <div class="bubble-body">
        <p>${renderSimpleMarkdown(text)}</p>
      </div>
    `;


    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
  }

  if (chatForm) {
    chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = chatInput.value.trim();
      if (!text) return;

      const activeModule = chatModuleSelect ? chatModuleSelect.value : "";
      appendChatMessage("user", text);
      chatInput.value = "";

      chatSendBtn.disabled = true;
      const spinner = chatSendBtn.querySelector(".btn-spinner");
      const btnText = chatSendBtn.querySelector(".btn-text");
      if (spinner) spinner.style.display = "inline";
      if (btnText) btnText.textContent = "Procesando...";

      const tempLoading = appendChatMessage("assistant", "Procesando solicitud...");

      try {
        const resp = await fetch("/api/chat/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({ message: text, module: activeModule })
        });

        const data = await resp.json();
        tempLoading.remove();

        if (data.answer) {
          appendChatMessage("assistant", data.answer, data.tools_executed);

          // Detección de borrador activo vs confirmación oficial
          const ans = data.answer.toLowerCase();
          const isDraftActive = ans.includes("borrador de presupuesto") ||
                                ans.includes("presupuesto preliminar") ||
                                ans.includes("actualizado:") ||
                                ans.includes("insumos presupuestados:") ||
                                ans.includes("si saco") ||
                                ans.includes("¿desea modificar") ||
                                ans.includes("¿deseas confirmar");

          const isConfirmed = ans.includes("presupuesto oficial generado") ||
                              ans.includes("guardado físicamente") ||
                              Boolean(data.presupuesto_created);

          if (chatDraftBanner) {
            if (isDraftActive && !isConfirmed) {
              chatDraftBanner.style.display = "flex";
              if (chatDraftBannerText) {
                chatDraftBannerText.textContent = "Borrador activo · Podés cambiar cantidades, quitar ítems o confirmar.";
              }
            } else if (isConfirmed) {
              chatDraftBanner.style.display = "none";
            }
          }

          // Refrescar archivos, índices, presupuestos, historial y dashboard
          if ((data.tools_executed && data.tools_executed.length > 0) || data.presupuesto_created || isConfirmed) {
            refreshFilesList();
            loadIndex();
            loadMemory();
            refreshPresupuestosList();
            loadHistorialPresupuestos();
            refreshDashboardMetrics();
          }
        } else if (!resp.ok || data.error) {
          appendChatMessage("assistant", "En este momento el asistente no está disponible, pero podés continuar utilizando las funciones administrativas del sistema.");
        }
      } catch (err) {
        tempLoading.remove();
        appendChatMessage("assistant", "En este momento hubo una interrupción temporal en la comunicación. Podés continuar utilizando las funciones administrativas del sistema.");
      } finally {
        chatSendBtn.disabled = false;
        if (spinner) spinner.style.display = "none";
        if (btnText) btnText.textContent = "Enviar";
        chatInput.focus();
      }
    });
  }

  // =========================================================================
  // 5. EXPLORADOR DE ARCHIVOS (CRUD REAL EN files_storage/)
  // =========================================================================
  const filesTbody = document.getElementById("filesTbody");
  const fileSearchInput = document.getElementById("fileSearchInput");
  const refreshFilesBtn = document.getElementById("refreshFilesBtn");
  const sidebarFilesCount = document.getElementById("sidebarFilesCount");
  const dashFilesCount = document.getElementById("dashFilesCount");
  const btnViewIndexQuick = document.getElementById("btnViewIndexQuick");

  function updateFilesTable(files) {
    if (!filesTbody) return;

    if (!files || files.length === 0) {
      filesTbody.innerHTML = `<tr><td colspan="5" class="text-center muted-text py-4">No hay archivos en este módulo o directorio.</td></tr>`;
      if (sidebarFilesCount) sidebarFilesCount.textContent = "0";
      return;
    }

    if (sidebarFilesCount) sidebarFilesCount.textContent = String(files.length);
    if (dashFilesCount) dashFilesCount.textContent = `${files.length} archivos`;

    filesTbody.innerHTML = files.map(file => {
      const icon = file.is_pdf ? "📕" : (file.is_editable ? "📝" : "📄");
      const canView = file.is_editable;
      const canDelete = !["INDEX.md", "MEMORY.md", "CHAT_HISTORY.json"].includes(file.name);

      return `
        <tr class="file-row" data-name="${escapeHtml(file.name)}" data-module="${escapeHtml(file.module)}">
          <td>
            <span class="row-icon">${icon}</span>
            <strong class="file-name-text">${escapeHtml(file.name)}</strong>
            <span class="file-rel-path">${escapeHtml(file.rel_path)}</span>
          </td>
          <td>
            <span class="badge badge-module">${escapeHtml(file.module)}</span>
          </td>
          <td>${file.size_str}</td>
          <td>${file.modified}</td>
          <td style="text-align: right;">
            ${canView ? `<button type="button" class="btn btn-xs btn-outline btn-view-file" data-path="${escapeHtml(file.rel_path)}">👁️ Ver / Editar</button>` : ""}
            <a href="${file.download_url}" class="btn btn-xs btn-outline" download title="Descargar">⬇️</a>
            ${canDelete ? `<button type="button" class="btn btn-xs btn-danger-outline btn-delete-file" data-path="${escapeHtml(file.rel_path)}" title="Eliminar archivo físico">🗑️</button>` : ""}
          </td>
        </tr>
      `;
    }).join("");

    attachFileActions();
  }

  async function refreshFilesList() {
    const mod = moduleFilterSelect ? moduleFilterSelect.value : "";
    try {
      const resp = await fetch(`/api/files/?module=${encodeURIComponent(mod)}`);
      const data = await resp.json();
      if (data.ok && data.files) {
        updateFilesTable(data.files);
        if (data.modules) updateModuleDropdowns(data.modules);
      }
    } catch (e) {
      console.error("Error al refrescar archivos:", e);
    }
  }

  function updateModuleDropdowns(modules) {
    const selects = [
      globalModuleSelect,
      moduleFilterSelect,
      chatModuleSelect,
      memoryModuleSelect,
      historyModuleSelect,
      indexModuleSelect,
      newFileModuleSelect
    ];
    selects.forEach(sel => {
      if (!sel) return;
      const cur = sel.value;
      const firstOpt = sel.options[0].outerHTML;
      sel.innerHTML = firstOpt + modules.map(m => `<option value="${m}">${m}/</option>`).join("");
      sel.value = cur;
    });

    const sidebarModulesCount = document.getElementById("sidebarModulesCount");
    if (sidebarModulesCount) sidebarModulesCount.textContent = String(modules.length);
  }

  if (moduleFilterSelect) {
    moduleFilterSelect.addEventListener("change", () => {
      syncAllModuleSelects(moduleFilterSelect.value);
      refreshFilesList();
    });
  }

  if (fileSearchInput) {
    fileSearchInput.addEventListener("input", () => {
      const q = fileSearchInput.value.toLowerCase().trim();
      const rows = filesTbody.querySelectorAll(".file-row");
      rows.forEach(r => {
        const name = (r.getAttribute("data-name") || "").toLowerCase();
        const mod = (r.getAttribute("data-module") || "").toLowerCase();
        r.style.display = (name.includes(q) || mod.includes(q)) ? "" : "none";
      });
    });
  }

  if (refreshFilesBtn) refreshFilesBtn.addEventListener("click", refreshFilesList);

  if (btnViewIndexQuick) {
    btnViewIndexQuick.addEventListener("click", () => {
      switchTab("tab-indice");
    });
  }

  // =========================================================================
  // 6. MODAL VISOR / EDITOR DE ARCHIVOS (LECTURA Y ESCRITURA FÍSICA)
  // =========================================================================
  const fileModal = document.getElementById("fileModal");
  const modalFileTitle = document.getElementById("modalFileTitle");
  const modalFilePathBadge = document.getElementById("modalFilePathBadge");
  const modalFileEditor = document.getElementById("modalFileEditor");
  const modalDownloadBtn = document.getElementById("modalDownloadBtn");
  const modalSaveFileBtn = document.getElementById("modalSaveFileBtn");
  const modalSaveNotice = document.getElementById("modalSaveNotice");
  const modalCloseBtn = document.getElementById("modalCloseBtn");
  const modalCloseBtn2 = document.getElementById("modalCloseBtn2");

  let currentViewingPath = "";

  function closeFileModal() {
    if (fileModal) fileModal.style.display = "none";
    if (modalSaveNotice) modalSaveNotice.style.display = "none";
  }

  if (modalCloseBtn) modalCloseBtn.onclick = closeFileModal;
  if (modalCloseBtn2) modalCloseBtn2.onclick = closeFileModal;

  async function openFileViewer(path) {
    currentViewingPath = path;
    try {
      const resp = await fetch(`/api/files/read/?path=${encodeURIComponent(path)}`);
      const data = await resp.json();
      if (data.ok) {
        modalFileTitle.textContent = `📄 ${path}`;
        modalFilePathBadge.textContent = `files_storage/${path}`;
        modalFileEditor.value = data.content;
        modalDownloadBtn.href = `/api/files/download/?path=${encodeURIComponent(path)}`;
        if (modalSaveNotice) modalSaveNotice.style.display = "none";
        fileModal.style.display = "flex";
      } else {
        alert("No se pudo leer el archivo: " + (data.error || ""));
      }
    } catch (e) {
      alert("Error accediendo al archivo: " + e.message);
    }
  }

  if (modalSaveFileBtn) {
    modalSaveFileBtn.onclick = async () => {
      if (!currentViewingPath) return;
      const content = modalFileEditor.value;

      modalSaveFileBtn.disabled = true;
      modalSaveFileBtn.textContent = "⏳ Guardando...";

      try {
        const resp = await fetch("/api/files/save/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({ filename: currentViewingPath, content })
        });
        const data = await resp.json();
        if (data.ok) {
          modalSaveNotice.style.display = "block";
          modalSaveNotice.textContent = `✅ Guardado exitoso en files_storage/${currentViewingPath} y auto-indexado en INDEX.md.`;
          refreshFilesList();
          loadIndex();
        } else {
          alert("Error al guardar: " + (data.error || ""));
        }
      } catch (err) {
        alert("Error de conexión: " + err.message);
      } finally {
        modalSaveFileBtn.disabled = false;
        modalSaveFileBtn.textContent = "💾 Guardar Cambios Físicos";
      }
    };
  }

  function attachFileActions() {
    document.querySelectorAll(".btn-view-file").forEach(b => {
      b.onclick = () => openFileViewer(b.getAttribute("data-path"));
    });

    document.querySelectorAll(".btn-delete-file").forEach(b => {
      b.onclick = async () => {
        const path = b.getAttribute("data-path");
        if (!confirm(`¿Eliminar físicamente el archivo '${path}'?\nEsta acción actualizará automáticamente INDEX.md.`)) {
          return;
        }

        try {
          const resp = await fetch("/api/files/delete/", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCsrf(),
            },
            body: JSON.stringify({ filename: path })
          });
          const data = await resp.json();
          if (data.ok) {
            refreshFilesList();
            loadIndex();
          } else {
            alert("Error al eliminar: " + (data.error || ""));
          }
        } catch (e) {
          alert("Error de red: " + e.message);
        }
      };
    });
  }

  attachFileActions();

  // =========================================================================
  // 7. MODAL: CREAR ARCHIVO FÍSICO NUEVO
  // =========================================================================
  const newFileModal = document.getElementById("newFileModal");
  const btnOpenNewFileModal = document.getElementById("btnOpenNewFileModal");
  const newFileCloseBtn = document.getElementById("newFileCloseBtn");
  const newFileCancelBtn = document.getElementById("newFileCancelBtn");
  const newFileForm = document.getElementById("newFileForm");
  const newFileNameInput = document.getElementById("newFileNameInput");
  const newFileContentInput = document.getElementById("newFileContentInput");

  function openNewFileModal() {
    if (newFileModal) {
      newFileNameInput.value = "";
      newFileContentInput.value = "";
      newFileModal.style.display = "flex";
      newFileNameInput.focus();
    }
  }

  function closeNewFileModal() {
    if (newFileModal) newFileModal.style.display = "none";
  }

  if (btnOpenNewFileModal) btnOpenNewFileModal.onclick = openNewFileModal;
  if (newFileCloseBtn) newFileCloseBtn.onclick = closeNewFileModal;
  if (newFileCancelBtn) newFileCancelBtn.onclick = closeNewFileModal;

  if (newFileForm) {
    newFileForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const filename = newFileNameInput.value.trim();
      const content = newFileContentInput.value;
      const module = newFileModuleSelect ? newFileModuleSelect.value : "";

      if (!filename) return;

      try {
        const resp = await fetch("/api/files/save/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({ filename, content, module })
        });
        const data = await resp.json();
        if (data.ok) {
          closeNewFileModal();
          alert(`Archivo '${data.rel_path}' creado físicamente e indexado con éxito.`);
          refreshFilesList();
          loadIndex();
        } else {
          alert("Error al crear archivo: " + (data.error || ""));
        }
      } catch (err) {
        alert("Error de conexión: " + err.message);
      }
    });
  }

  // =========================================================================
  // 8. MODAL: CREAR MÓDULO AISLADO
  // =========================================================================
  const newFolderModal = document.getElementById("newFolderModal");
  const btnOpenNewFolderModal = document.getElementById("btnOpenNewFolderModal");
  const btnCreateModuleModal = document.getElementById("btnCreateModuleModal");
  const newFolderCloseBtn = document.getElementById("newFolderCloseBtn");
  const newFolderCancelBtn = document.getElementById("newFolderCancelBtn");
  const newFolderForm = document.getElementById("newFolderForm");
  const newFolderName = document.getElementById("newFolderName");
  const newFolderDesc = document.getElementById("newFolderDesc");

  function openFolderModal(prefill = "") {
    if (newFolderModal) {
      newFolderName.value = prefill;
      newFolderDesc.value = "";
      newFolderModal.style.display = "flex";
      newFolderName.focus();
    }
  }

  function closeFolderModal() {
    if (newFolderModal) newFolderModal.style.display = "none";
  }

  if (btnOpenNewFolderModal) btnOpenNewFolderModal.onclick = () => openFolderModal();
  if (btnCreateModuleModal) btnCreateModuleModal.onclick = () => openFolderModal();
  if (newFolderCloseBtn) newFolderCloseBtn.onclick = closeFolderModal;
  if (newFolderCancelBtn) newFolderCancelBtn.onclick = closeFolderModal;

  if (newFolderForm) {
    newFolderForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const folder_name = newFolderName.value.trim();
      const description = newFolderDesc.value.trim();
      if (!folder_name) return;

      try {
        const resp = await fetch("/api/folder/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({ folder_name, description })
        });
        const data = await resp.json();
        if (data.ok) {
          closeFolderModal();
          alert(`Módulo '${data.folder}/' creado físicamente con INDEX.md, MEMORY.md y CHAT_HISTORY.json.`);
          refreshFilesList();
          loadModules();
          loadIndex();
        } else {
          alert("Error al crear módulo: " + (data.error || ""));
        }
      } catch (err) {
        alert("Error de red: " + err.message);
      }
    });
  }

  // =========================================================================
  // 9. MEMORIA PERSISTENTE (MEMORY.md)
  // =========================================================================
  const memoryContentDisplay = document.getElementById("memoryContentDisplay");
  const memoryViewerTitle = document.getElementById("memoryViewerTitle");
  const refreshMemoryBtn = document.getElementById("refreshMemoryBtn");
  const addMemoryForm = document.getElementById("addMemoryForm");
  const newMemoryRule = document.getElementById("newMemoryRule");

  async function loadMemory() {
    if (!memoryContentDisplay) return;
    const mod = memoryModuleSelect ? memoryModuleSelect.value : "";
    try {
      const resp = await fetch(`/api/memory/?module=${encodeURIComponent(mod)}`);
      const data = await resp.json();
      if (data.ok && data.memory) {
        memoryContentDisplay.textContent = data.memory;
        if (memoryViewerTitle) {
          memoryViewerTitle.textContent = mod
            ? `Contenido físico en disco: files_storage/${mod}/MEMORY.md`
            : "Contenido físico en disco: files_storage/MEMORY.md";
        }
      }
    } catch (e) {
      console.error("Error cargando memoria:", e);
    }
  }

  if (memoryModuleSelect) {
    memoryModuleSelect.addEventListener("change", loadMemory);
  }
  if (refreshMemoryBtn) {
    refreshMemoryBtn.addEventListener("click", loadMemory);
  }

  if (addMemoryForm) {
    addMemoryForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const note = newMemoryRule.value.trim();
      const mod = memoryModuleSelect ? memoryModuleSelect.value : "";
      if (!note) return;

      const saveBtn = document.getElementById("saveMemoryBtn");
      saveBtn.disabled = true;

      try {
        const resp = await fetch("/api/memory/add/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({ note, module: mod })
        });
        const data = await resp.json();
        if (data.ok) {
          newMemoryRule.value = "";
          if (data.memory) memoryContentDisplay.textContent = data.memory;
          alert("Regla permanente guardada físicamente en MEMORY.md. Sobrevivirá a reinicios.");
        } else {
          alert("Error: " + (data.error || ""));
        }
      } catch (err) {
        alert("Error de conexión: " + err.message);
      } finally {
        saveBtn.disabled = false;
      }
    });
  }

  // =========================================================================
  // 10. HISTORIAL DE CONVERSACIONES (CHAT_HISTORY.json)
  // =========================================================================
  const historyMessagesList = document.getElementById("historyMessagesList");
  const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
  const clearHistoryBtn = document.getElementById("clearHistoryBtn");

  async function loadHistory() {
    if (!historyMessagesList) return;
    const mod = historyModuleSelect ? historyModuleSelect.value : "";
    try {
      const resp = await fetch(`/api/history/?module=${encodeURIComponent(mod)}`);
      const data = await resp.json();
      if (data.ok && data.history) {
        if (data.history.length === 0) {
          historyMessagesList.innerHTML = `<div class="muted-text text-center py-4">No hay interacciones registradas en este módulo (${mod || "Global"}).</div>`;
          return;
        }

        historyMessagesList.innerHTML = data.history.map((msg, i) => {
          const isUser = msg.role === "user";
          const roleClass = isUser ? "role-user" : "role-assistant";
          const roleName = isUser ? "👤 Administradora" : "🤖 Asistente Claude";
          const content = typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content);

          return `
            <div class="history-card ${roleClass}">
              <div class="history-head">
                <span>${roleName}</span>
                <span>#${i + 1}</span>
              </div>
              <div class="history-body">${renderSimpleMarkdown(content)}</div>
            </div>
          `;
        }).join("");
      }
    } catch (e) {
      historyMessagesList.innerHTML = `<div class="text-danger">Error cargando historial: ${e.message}</div>`;
    }
  }

  if (historyModuleSelect) historyModuleSelect.addEventListener("change", loadHistory);
  if (refreshHistoryBtn) refreshHistoryBtn.addEventListener("click", loadHistory);

  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener("click", async () => {
      const mod = historyModuleSelect ? historyModuleSelect.value : "";
      if (!confirm(`¿Limpiar el historial de CHAT_HISTORY.json para el módulo '${mod || "Global"}'?`)) {
        return;
      }

      try {
        const resp = await fetch("/api/history/clear/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({ module: mod })
        });
        const data = await resp.json();
        if (data.ok) {
          loadHistory();
        }
      } catch (e) {
        alert("Error limpiando historial: " + e.message);
      }
    });
  }

  // =========================================================================
  // 11. MÓDULOS AISLADOS (CARDS Y GESTIÓN)
  // =========================================================================
  const modulesCardsContainer = document.getElementById("modulesCardsContainer");
  const refreshModulesBtn = document.getElementById("refreshModulesBtn");

  async function loadModules() {
    if (!modulesCardsContainer) return;
    try {
      const resp = await fetch("/api/modules/");
      const data = await resp.json();
      if (data.ok && data.modules) {
        modulesCardsContainer.innerHTML = data.modules.map(mod => `
          <div class="module-card">
            <div class="mod-card-header">
              <span class="mod-icon">📁</span>
              <h4>${escapeHtml(mod.name)}/</h4>
              <span class="badge badge-module">${mod.file_count} archivos</span>
            </div>
            <p class="mod-desc">${escapeHtml(mod.description)}</p>
            <div class="mod-badges">
              <span class="tag-check">${mod.has_index ? "✓ INDEX.md" : "✗ Sin INDEX"}</span>
              <span class="tag-check">${mod.has_memory ? "✓ MEMORY.md" : "✗ Sin MEMORY"}</span>
              <span class="tag-check">${mod.has_history ? "✓ Historial" : "✗ Sin Historial"}</span>
            </div>
            <div class="mod-card-actions">
              <button type="button" class="btn btn-xs btn-outline btn-filter-by-mod" data-module="${escapeHtml(mod.name)}">
                📁 Ver Archivos
              </button>
              <button type="button" class="btn btn-xs btn-primary btn-chat-in-mod" data-module="${escapeHtml(mod.name)}">
                🤖 Operar con Claude
              </button>
            </div>
          </div>
        `).join("");

        attachModuleCardActions();
      }
    } catch (e) {
      console.error("Error al cargar módulos:", e);
    }
  }

  function attachModuleCardActions() {
    document.querySelectorAll(".btn-filter-by-mod").forEach(b => {
      b.onclick = () => {
        const mod = b.getAttribute("data-module");
        syncAllModuleSelects(mod);
        switchTab("tab-archivos");
        refreshFilesList();
      };
    });

    document.querySelectorAll(".btn-chat-in-mod").forEach(b => {
      b.onclick = () => {
        const mod = b.getAttribute("data-module");
        syncAllModuleSelects(mod);
        switchTab("tab-chat");
      };
    });
  }

  if (refreshModulesBtn) refreshModulesBtn.addEventListener("click", loadModules);

  // Chips del dashboard
  document.querySelectorAll(".module-chip").forEach(chip => {
    chip.onclick = () => {
      const mod = chip.getAttribute("data-module");
      syncAllModuleSelects(mod);
      switchTab("tab-archivos");
      refreshFilesList();
    };
  });

  // =========================================================================
  // 12. ÍNDICE SEMÁNTICO (INDEX.md)
  // =========================================================================
  const indexContentDisplay = document.getElementById("indexContentDisplay");
  const refreshIndexBtn = document.getElementById("refreshIndexBtn");
  const btnRebuildIndex = document.getElementById("btnRebuildIndex");

  async function loadIndex() {
    if (!indexContentDisplay) return;
    const mod = indexModuleSelect ? indexModuleSelect.value : "";
    try {
      const resp = await fetch(`/api/index/?module=${encodeURIComponent(mod)}`);
      const data = await resp.json();
      if (data.ok && data.index) {
        indexContentDisplay.textContent = data.index;
      }
    } catch (e) {
      console.error("Error cargando índice:", e);
    }
  }

  if (indexModuleSelect) indexModuleSelect.addEventListener("change", loadIndex);
  if (refreshIndexBtn) refreshIndexBtn.addEventListener("click", loadIndex);

  if (btnRebuildIndex) {
    btnRebuildIndex.addEventListener("click", async () => {
      const mod = indexModuleSelect ? indexModuleSelect.value : "";
      btnRebuildIndex.disabled = true;
      btnRebuildIndex.textContent = "⏳ Reconstruyendo...";

      try {
        const resp = await fetch("/api/index/rebuild/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({ module: mod })
        });
        const data = await resp.json();
        if (data.ok) {
          if (data.index) indexContentDisplay.textContent = data.index;
          alert("Índice INDEX.md actualizado y sincronizado en disco.");
          refreshFilesList();
        } else {
          alert("Error: " + (data.error || ""));
        }
      } catch (e) {
        alert("Error de red: " + e.message);
      } finally {
        btnRebuildIndex.disabled = false;
        btnRebuildIndex.textContent = "⚡ Reconstruir Índice Ahora";
      }
    });
  }

  // =========================================================================
  // 13. GENERADOR DE PRESUPUESTOS (PDF REPORTLAB)
  // =========================================================================
  const productsTbody = document.getElementById("productsTbody");
  const addRowBtn = document.getElementById("addRowBtn");
  const presIvaSelect = document.getElementById("presIvaSelect");
  const summarySubtotal = document.getElementById("summarySubtotal");
  const summaryIva = document.getElementById("summaryIva");
  const summaryIvaLabel = document.getElementById("summaryIvaLabel");
  const summaryTotal = document.getElementById("summaryTotal");
  const presupuestoForm = document.getElementById("presupuestoForm");
  const aiParseBtn = document.getElementById("aiParseBtn");
  const aiParseInput = document.getElementById("aiParseInput");
  const aiParseNotice = document.getElementById("aiParseNotice");
  const presupuestoSuccessBox = document.getElementById("presupuestoSuccessBox");
  const downloadLatestPdfBtn = document.getElementById("downloadLatestPdfBtn");
  const refreshPresupuestosBtn = document.getElementById("refreshPresupuestosBtn");

  function recalculateBudgetTotals() {
    let subtotal = 0;
    const rows = productsTbody.querySelectorAll(".product-row");

    rows.forEach(row => {
      const cantInput = row.querySelector(".row-cant");
      const priceInput = row.querySelector(".row-price");
      const subCell = row.querySelector(".row-subtotal-cell");

      const cant = parseFloat(cantInput.value) || 0;
      const price = parseFloat(priceInput.value) || 0;
      const rowSub = cant * price;
      subtotal += rowSub;

      if (subCell) {
        subCell.textContent = formatCurrency(rowSub);
      }
    });

    const ivaPct = parseFloat(presIvaSelect.value) || 0;
    const ivaMonto = subtotal * (ivaPct / 100);
    const total = subtotal + ivaMonto;

    if (summarySubtotal) summarySubtotal.textContent = formatCurrency(subtotal);
    if (summaryIvaLabel) summaryIvaLabel.textContent = `IVA (${ivaPct}%):`;
    if (summaryIva) summaryIva.textContent = formatCurrency(ivaMonto);
    if (summaryTotal) summaryTotal.textContent = formatCurrency(total);

    return { subtotal, ivaPct, ivaMonto, total };
  }

  function attachBudgetRowEvents(row) {
    const cantInput = row.querySelector(".row-cant");
    const priceInput = row.querySelector(".row-price");
    const delBtn = row.querySelector(".btn-del-row");

    cantInput.addEventListener("input", recalculateBudgetTotals);
    priceInput.addEventListener("input", recalculateBudgetTotals);

    if (delBtn) {
      delBtn.addEventListener("click", () => {
        const allRows = productsTbody.querySelectorAll(".product-row");
        if (allRows.length > 1) {
          row.remove();
          recalculateBudgetTotals();
        } else {
          alert("El presupuesto debe contener al menos un producto.");
        }
      });
    }
  }

  if (productsTbody) {
    productsTbody.querySelectorAll(".product-row").forEach(attachBudgetRowEvents);
  }

  if (addRowBtn) {
    addRowBtn.addEventListener("click", () => {
      const tr = document.createElement("tr");
      tr.className = "product-row";
      tr.innerHTML = `
        <td>
          <input type="text" class="form-control row-desc" placeholder="Descripción del producto o insumo" required>
        </td>
        <td>
          <input type="number" class="form-control row-cant" min="1" step="1" value="1" required>
        </td>
        <td>
          <input type="number" class="form-control row-price" min="0" step="any" placeholder="0.00" value="0" required>
        </td>
        <td class="row-subtotal-cell">$ 0,00</td>
        <td>
          <button type="button" class="btn-del-row" title="Eliminar fila">✕</button>
        </td>
      `;
      productsTbody.appendChild(tr);
      attachBudgetRowEvents(tr);
      tr.querySelector(".row-desc").focus();
    });
  }

  if (presIvaSelect) presIvaSelect.addEventListener("change", recalculateBudgetTotals);

  // Asistencia con IA para interpretar pedidos
  if (aiParseBtn && aiParseInput) {
    aiParseBtn.addEventListener("click", async () => {
      const text = aiParseInput.value.trim();
      if (!text) {
        alert("Ingresá la solicitud a interpretar.");
        return;
      }

      aiParseBtn.disabled = true;
      aiParseBtn.textContent = "Interpretando con Claude...";
      aiParseNotice.style.display = "none";

      try {
        const resp = await fetch("/api/presupuestos/ai-parse/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({ solicitud: text })
        });
        const res = await resp.json();

        if (res.ok && res.data) {
          const d = res.data;
          if (d.cliente) document.getElementById("presCliente").value = d.cliente;
          if (d.institucion) document.getElementById("presInstitucion").value = d.institucion;
          if (d.validez) document.getElementById("presValidez").value = d.validez;
          if (d.observaciones) document.getElementById("presObs").value = d.observaciones;

          if (d.productos && Array.isArray(d.productos) && d.productos.length > 0) {
            productsTbody.innerHTML = "";
            d.productos.forEach(prod => {
              const tr = document.createElement("tr");
              tr.className = "product-row";
              const pu = (prod.precio_unitario !== null && prod.precio_unitario !== undefined) ? prod.precio_unitario : 0;
              tr.innerHTML = `
                <td>
                  <input type="text" class="form-control row-desc" value="${escapeHtml(prod.descripcion || '')}" required>
                </td>
                <td>
                  <input type="number" class="form-control row-cant" min="1" step="1" value="${prod.cantidad || 1}" required>
                </td>
                <td>
                  <input type="number" class="form-control row-price" min="0" step="any" placeholder="0.00" value="${pu}" required>
                </td>
                <td class="row-subtotal-cell">$ 0,00</td>
                <td>
                  <button type="button" class="btn-del-row" title="Eliminar fila">✕</button>
                </td>
              `;
              productsTbody.appendChild(tr);
              attachBudgetRowEvents(tr);
            });
            recalculateBudgetTotals();
          }

          if (d.missing_prices) {
            aiParseNotice.style.display = "block";
            aiParseNotice.innerHTML = `⚠️ <b>Precios faltantes:</b> La IA interpretó el cliente y la cantidad de productos, pero <b>no inventa precios</b>. Por favor completá el precio unitario en la tabla.`;
          } else if (d.notice) {
            aiParseNotice.style.display = "block";
            aiParseNotice.innerHTML = `ℹ️ ${escapeHtml(d.notice)}`;
          }
        } else {
          alert("Error interpretando solicitud: " + (res.error || "Formato no válido"));
        }
      } catch (err) {
        alert("Error de conexión: " + err.message);
      } finally {
        aiParseBtn.disabled = false;
        aiParseBtn.textContent = "Interpretar con IA";
      }
    });
  }

  // Generar presupuesto PDF oficial
  if (presupuestoForm) {
    presupuestoForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const cliente = document.getElementById("presCliente").value.trim();
      const institucion = document.getElementById("presInstitucion").value.trim();
      const validez = document.getElementById("presValidez").value.trim();
      const observaciones = document.getElementById("presObs").value.trim();
      const iva_porcentaje = parseFloat(presIvaSelect.value) || 21.0;

      const rows = productsTbody.querySelectorAll(".product-row");
      const productos = [];

      for (const row of rows) {
        const desc = row.querySelector(".row-desc").value.trim();
        const cant = parseFloat(row.querySelector(".row-cant").value) || 0;
        const pu = parseFloat(row.querySelector(".row-price").value);

        if (!desc) {
          alert("Todos los productos deben tener descripción.");
          return;
        }
        if (isNaN(pu) || pu < 0) {
          alert(`El producto '${desc}' tiene un precio no válido. Indicá un valor numérico.`);
          return;
        }

        productos.push({
          descripcion: desc,
          cantidad: cant,
          precio_unitario: pu
        });
      }

      const submitBtn = document.getElementById("generatePresupuestoBtn");
      submitBtn.disabled = true;
      submitBtn.textContent = "⏳ Generando PDF Oficial con ReportLab...";

      try {
        const resp = await fetch("/api/presupuestos/generate/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({
            cliente,
            institucion,
            validez,
            observaciones,
            iva_porcentaje,
            productos
          })
        });

        const data = await resp.json();

        if (data.ok && data.presupuesto) {
          const p = data.presupuesto;
          presupuestoSuccessBox.style.display = "block";
          document.getElementById("presupuestoSuccessDesc").innerHTML = `
            Se ha emitido el presupuesto oficial <b>${p.numero}</b> para <b>${escapeHtml(p.cliente)}</b>.<br>
            <b>Subtotal:</b> ${formatCurrency(p.subtotal)} | 
            <b>IVA (${p.iva_porcentaje}%):</b> ${formatCurrency(p.iva_monto)} | 
            <b>TOTAL:</b> ${formatCurrency(p.total)}<br>
            Guardado físicamente en: <code>files_storage/${p.rel_path}</code>
          `;
          downloadLatestPdfBtn.href = p.download_url;
          downloadLatestPdfBtn.setAttribute("download", p.filename);

          refreshPresupuestosList();
          loadHistorialPresupuestos();
          refreshDashboardMetrics();
          refreshFilesList();
          loadIndex();
          presupuestoSuccessBox.scrollIntoView({ behavior: "smooth" });
        } else {
          alert("Error generando presupuesto: " + (data.error || ""));
        }
      } catch (err) {
        alert("Error de red: " + err.message);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "📄 Generar Presupuesto y PDF Oficial en disco";
      }
    });
  }

  async function refreshPresupuestosList() {
    const listEl = document.getElementById("presupuestosFileList");
    if (!listEl) return;

    try {
      const resp = await fetch("/api/files/?module=presupuestos");
      const data = await resp.json();
      if (data.ok && data.files) {
        const pdfs = data.files.filter(f => f.is_pdf);
        if (pdfs.length === 0) {
          listEl.innerHTML = `<div class="muted-text py-2">No hay presupuestos PDF guardados aún.</div>`;
          return;
        }

        listEl.innerHTML = pdfs.map(f => `
          <div class="presupuesto-item">
            <div>
              <strong>📕 ${escapeHtml(f.name)}</strong>
              <div class="muted-text">${f.modified} · ${f.size_str}</div>
            </div>
            <a href="${f.download_url}" class="btn btn-xs btn-outline" download>⬇️ Descargar PDF</a>
          </div>
        `).join("");
      }
    } catch (e) {
      listEl.innerHTML = `<div class="text-danger">Error cargando presupuestos: ${e.message}</div>`;
    }
  }

  if (refreshPresupuestosBtn) refreshPresupuestosBtn.addEventListener("click", refreshPresupuestosList);

  // =========================================================================
  // 14. COMPROBACIÓN EN VIVO DE UMSA-DJANGO
  // =========================================================================
  const pingUmsaBtn = document.getElementById("pingUmsaBtn");
  const umsaStatusBadge = document.getElementById("umsaStatusBadge");
  const topUmsaChip = document.getElementById("topUmsaChip");
  const sidebarUmsaIndicator = document.getElementById("sidebarUmsaIndicator");

  if (pingUmsaBtn) {
    pingUmsaBtn.addEventListener("click", async () => {
      pingUmsaBtn.disabled = true;
      pingUmsaBtn.textContent = "⏳ Comprobando conexión...";

      try {
        const resp = await fetch("/api/umsa/");
        const data = await resp.json();
        const st = data.status || {};

        if (st.online) {
          if (umsaStatusBadge) {
            umsaStatusBadge.className = "badge badge-success";
            umsaStatusBadge.textContent = `CONECTADO (HTTP ${st.status_code || 200})`;
          }
          if (topUmsaChip) {
            topUmsaChip.className = "topbar-status-chip chip-online";
            topUmsaChip.querySelector("span:last-child").textContent = "UMSA-Django: 200 OK";
          }
          if (sidebarUmsaIndicator) {
            sidebarUmsaIndicator.className = "link-indicator indicator-online";
          }
        } else {
          if (umsaStatusBadge) {
            umsaStatusBadge.className = "badge badge-danger";
            umsaStatusBadge.textContent = "SIN RESPUESTA";
          }
          if (topUmsaChip) {
            topUmsaChip.className = "topbar-status-chip chip-offline";
            topUmsaChip.querySelector("span:last-child").textContent = "UMSA-Django: Offline";
          }
          if (sidebarUmsaIndicator) {
            sidebarUmsaIndicator.className = "link-indicator indicator-offline";
          }
        }
      } catch (err) {
        if (umsaStatusBadge) {
          umsaStatusBadge.className = "badge badge-danger";
          umsaStatusBadge.textContent = "ERROR AL VERIFICAR";
        }
      } finally {
        pingUmsaBtn.disabled = false;
        pingUmsaBtn.textContent = "🔄 Comprobar Conexión Ahora";
      }
    });
  }

  // =========================================================================
  // 15. BOTONES DE PRUEBAS DIRECTAS DE LA GUÍA DE CLASE
  // =========================================================================
  const btnTestManualFile = document.getElementById("btnTestManualFile");
  const btnTestToolCalling = document.getElementById("btnTestToolCalling");
  const btnTestMemory = document.getElementById("btnTestMemory");
  const btnTestIsolatedModule = document.getElementById("btnTestIsolatedModule");

  // Prueba 1: Archivo manual proyecto.txt
  if (btnTestManualFile) {
    btnTestManualFile.addEventListener("click", async () => {
      try {
        const resp = await fetch("/api/files/save/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({
            filename: "proyecto.txt",
            content: "PRUEBA 1 GUÍA: Verificación de archivo físico creado manualmente en files_storage/proyecto.txt.",
            module: ""
          })
        });
        const data = await resp.json();
        if (data.ok) {
          alert("PRUEBA 1 COMPLETADA:\nSe creó físicamente 'files_storage/proyecto.txt' y se actualizó INDEX.md.");
          switchTab("tab-archivos");
          refreshFilesList();
          loadIndex();
        }
      } catch (e) {
        alert("Error en prueba 1: " + e.message);
      }
    });
  }

  // Prueba 2 & 3: Tool Calling tareasfuturas.md
  if (btnTestToolCalling) {
    btnTestToolCalling.addEventListener("click", () => {
      switchTab("tab-chat");
      if (chatInput) {
        chatInput.value = "Por favor crea el archivo tareasfuturas.md con 3 tareas técnicas y actualiza la memoria persistente.";
        chatInput.focus();
      }
    });
  }

  // Prueba 4: Memoria persistente
  if (btnTestMemory) {
    btnTestMemory.addEventListener("click", () => {
      switchTab("tab-memoria");
      if (newMemoryRule) {
        newMemoryRule.value = "Todos los documentos nuevos deben tener una sección de Criterios de Aceptación y nuestro framework base es Django.";
        newMemoryRule.focus();
      }
    });
  }

  // Prueba 5: Módulo aislado libreria
  if (btnTestIsolatedModule) {
    btnTestIsolatedModule.addEventListener("click", () => {
      openFolderModal("libreria");
    });
  }

  // =========================================================================
  // =========================================================================
  // INVENTARIO DE INSUMOS MÉDICOS (STOCK ILIMITADO & FOTOGRAFÍAS INDIVIDUALES)
  // =========================================================================
  const refreshInventarioBtn = document.getElementById("refreshInventarioBtn");
  const inventarioTable = document.getElementById("inventarioTable");
  const btnOpenNewInsumoModal = document.getElementById("btnOpenNewInsumoModal");
  const insumoEditModal = document.getElementById("insumoEditModal");
  const insumoModalCloseBtn = document.getElementById("insumoModalCloseBtn");
  const insumoModalCancelBtn = document.getElementById("insumoModalCancelBtn");
  const insumoEditForm = document.getElementById("insumoEditForm");
  const insumoModalTitle = document.getElementById("insumoModalTitle");
  const insumoIdInput = document.getElementById("insumoIdInput");
  const insumoQuitarImagenInput = document.getElementById("insumoQuitarImagenInput");
  const insumoImagePreview = document.getElementById("insumoImagePreview");
  const insumoFileInput = document.getElementById("insumoFileInput");
  const btnSelectInsumoImage = document.getElementById("btnSelectInsumoImage");
  const btnRemoveInsumoImage = document.getElementById("btnRemoveInsumoImage");
  const insumoNombreInput = document.getElementById("insumoNombreInput");
  const insumoPresentacionInput = document.getElementById("insumoPresentacionInput");
  const insumoPrecioInput = document.getElementById("insumoPrecioInput");
  const insumoEstadoInput = document.getElementById("insumoEstadoInput");

  function openInsumoModal(data = null) {
    if (!insumoEditModal) return;
    if (data) {
      if (insumoModalTitle) insumoModalTitle.textContent = `✏️ Editar Insumo: ${data.producto || ""}`;
      if (insumoIdInput) insumoIdInput.value = data.id || "";
      if (insumoNombreInput) insumoNombreInput.value = data.producto || "";
      if (insumoPresentacionInput) insumoPresentacionInput.value = data.presentacion || "";
      if (insumoPrecioInput) insumoPrecioInput.value = data.precio_unitario ?? "";
      if (insumoEstadoInput) insumoEstadoInput.value = data.estado || "Disponible";
      if (insumoImagePreview) insumoImagePreview.src = data.imagen || "/media/productos/placeholder.svg";
      if (insumoQuitarImagenInput) insumoQuitarImagenInput.value = "0";
    } else {
      if (insumoModalTitle) insumoModalTitle.textContent = "➕ Nuevo Insumo Médico";
      if (insumoIdInput) insumoIdInput.value = "";
      if (insumoNombreInput) insumoNombreInput.value = "";
      if (insumoPresentacionInput) insumoPresentacionInput.value = "";
      if (insumoPrecioInput) insumoPrecioInput.value = "";
      if (insumoEstadoInput) insumoEstadoInput.value = "Disponible";
      if (insumoImagePreview) insumoImagePreview.src = "/media/productos/placeholder.svg";
      if (insumoQuitarImagenInput) insumoQuitarImagenInput.value = "0";
    }
    if (insumoFileInput) insumoFileInput.value = "";
    insumoEditModal.style.display = "flex";
    if (insumoNombreInput) insumoNombreInput.focus();
  }

  function closeInsumoModal() {
    if (insumoEditModal) insumoEditModal.style.display = "none";
  }

  if (insumoModalCloseBtn) insumoModalCloseBtn.addEventListener("click", closeInsumoModal);
  if (insumoModalCancelBtn) insumoModalCancelBtn.addEventListener("click", closeInsumoModal);
  if (insumoEditModal) {
    insumoEditModal.addEventListener("click", (e) => {
      if (e.target === insumoEditModal) closeInsumoModal();
    });
  }

  if (btnOpenNewInsumoModal) {
    btnOpenNewInsumoModal.addEventListener("click", () => openInsumoModal(null));
  }

  if (btnSelectInsumoImage && insumoFileInput) {
    btnSelectInsumoImage.addEventListener("click", () => {
      insumoFileInput.click();
    });
  }

  if (insumoFileInput) {
    insumoFileInput.addEventListener("change", () => {
      if (insumoFileInput.files && insumoFileInput.files[0]) {
        const file = insumoFileInput.files[0];
        const previewUrl = URL.createObjectURL(file);
        if (insumoImagePreview) insumoImagePreview.src = previewUrl;
        if (insumoQuitarImagenInput) insumoQuitarImagenInput.value = "0";
      }
    });
  }

  if (btnRemoveInsumoImage) {
    btnRemoveInsumoImage.addEventListener("click", () => {
      if (insumoImagePreview) insumoImagePreview.src = "/media/productos/placeholder.svg";
      if (insumoQuitarImagenInput) insumoQuitarImagenInput.value = "1";
      if (insumoFileInput) insumoFileInput.value = "";
    });
  }

  if (insumoEditForm) {
    insumoEditForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btnSave = document.getElementById("btnSaveInsumo");
      const origText = btnSave ? btnSave.textContent : "";
      if (btnSave) {
        btnSave.disabled = true;
        btnSave.textContent = "⏳ Guardando...";
      }
      try {
        const formData = new FormData(insumoEditForm);
        const resp = await fetch("/api/inventario/save/", {
          method: "POST",
          body: formData
        });
        const data = await resp.json();
        if (data.ok) {
          closeInsumoModal();
          await refreshInventarioList();
          if (typeof refreshDashboardMetrics === "function") {
            refreshDashboardMetrics();
          }
        } else {
          alert("Error al guardar insumo: " + (data.error || ""));
        }
      } catch (err) {
        console.error("Error al guardar insumo:", err);
        alert("Error de conexión al guardar el insumo.");
      } finally {
        if (btnSave) {
          btnSave.disabled = false;
          btnSave.textContent = origText;
        }
      }
    });
  }

  function attachInsumoTableEvents() {
    if (!inventarioTable) return;
    inventarioTable.querySelectorAll(".btn-edit-insumo").forEach(btn => {
      btn.onclick = () => {
        const item = {
          id: btn.getAttribute("data-id") || "",
          producto: btn.getAttribute("data-producto") || "",
          presentacion: btn.getAttribute("data-presentacion") || "",
          precio_unitario: btn.getAttribute("data-precio") || "",
          estado: btn.getAttribute("data-estado") || "Disponible",
          imagen: btn.getAttribute("data-imagen") || "/media/productos/placeholder.svg"
        };
        openInsumoModal(item);
      };
    });

    inventarioTable.querySelectorAll(".btn-ask-single-inv").forEach(btn => {
      btn.onclick = () => {
        const prompt = btn.getAttribute("data-prompt");
        if (prompt) {
          switchTab("tab-chat");
          if (chatInput) {
            chatInput.value = prompt;
            chatInput.focus();
          }
        }
      };
    });
  }

  async function refreshInventarioList() {
    if (!inventarioTable) return;
    try {
      const resp = await fetch("/api/inventario/");
      const data = await resp.json();
      if (data.ok && Array.isArray(data.inventario)) {
        const tbody = inventarioTable.querySelector("tbody");
        if (tbody) {
          if (data.inventario.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center muted-text py-4">No se encontraron productos en el inventario.</td></tr>`;
          } else {
            tbody.innerHTML = data.inventario.map(item => `
              <tr class="inv-row" data-id="${escapeHtml(item.id || '')}" data-producto="${escapeHtml(item.producto)}" data-precio="${escapeHtml(item.precio_unitario)}">
                <td style="text-align: center;">
                  <div class="inv-thumb-wrap">
                    <img src="${escapeHtml(item.imagen || '/media/productos/placeholder.svg')}" 
                         alt="${escapeHtml(item.producto)}" 
                         class="inv-thumb-img" 
                         loading="lazy" 
                         onerror="this.onerror=null;this.src='/media/productos/placeholder.svg';">
                  </div>
                </td>
                <td><strong class="inv-product-name">${escapeHtml(item.producto)}</strong></td>
                <td><span class="muted-text">${escapeHtml(item.presentacion || '')}</span></td>
                <td style="text-align: right; font-weight: 700; color: var(--primary-navy);">$${Number(item.precio_unitario || 0).toLocaleString("es-AR")}</td>
                <td style="text-align: center;">
                  <span class="badge badge-success" style="font-size: 11px; padding: 4px 10px; font-weight: 800; letter-spacing: 0.5px;">${escapeHtml(item.stock || "ILIMITADO")}</span>
                </td>
                <td style="text-align: center;"><span class="badge badge-subtle">${escapeHtml(item.estado || "Disponible")}</span></td>
                <td style="text-align: right;">
                  <div class="action-buttons-inline">
                    <button type="button" class="btn btn-xs btn-outline btn-edit-insumo" 
                            data-id="${escapeHtml(item.id || '')}" 
                            data-producto="${escapeHtml(item.producto)}" 
                            data-presentacion="${escapeHtml(item.presentacion || '')}" 
                            data-precio="${escapeHtml(item.precio_unitario)}" 
                            data-stock="${escapeHtml(item.stock || 'ILIMITADO')}" 
                            data-estado="${escapeHtml(item.estado || 'Disponible')}" 
                            data-imagen="${escapeHtml(item.imagen || '/media/productos/placeholder.svg')}" 
                            title="Editar insumo e imagen">
                      ✏️ Editar
                    </button>
                    <button type="button" class="btn btn-xs btn-outline btn-ask-single-inv" 
                            data-prompt="¿Cuánto cuesta ${escapeHtml(item.producto)}?" 
                            title="Consultar en Asistente">
                      💬
                    </button>
                  </div>
                </td>
              </tr>
            `).join("");
          }
          attachInsumoTableEvents();
        }
      }
    } catch (e) {
      console.error("Error al refrescar inventario:", e);
    }
  }

  if (refreshInventarioBtn) {
    refreshInventarioBtn.addEventListener("click", () => {
      refreshInventarioList();
    });
  }

  // Activar botones para los elementos ya renderizados en el HTML del servidor
  attachInsumoTableEvents();

  // Botones de consulta rápida de inventario con Claude
  document.querySelectorAll(".btn-ask-inv").forEach(btn => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-prompt");
      if (prompt) {
        switchTab("tab-chat");
        if (chatInput) {
          chatInput.value = prompt;
          chatInput.focus();
        }
      }
    });
  });

  // =========================================================================
  // 16. BÚSQUEDA GLOBAL UNIFICADA CON RESULTADOS PREDICTIVOS
  // =========================================================================
  const globalSearchInput = document.getElementById("globalSearchInput");
  const globalSearchDropdown = document.getElementById("globalSearchDropdown");
  const globalSearchClearBtn = document.getElementById("globalSearchClearBtn");
  let searchDebounceTimer = null;

  function closeGlobalSearch() {
    if (globalSearchDropdown) globalSearchDropdown.style.display = "none";
  }

  if (globalSearchClearBtn) {
    globalSearchClearBtn.addEventListener("click", () => {
      if (globalSearchInput) {
        globalSearchInput.value = "";
        globalSearchInput.focus();
      }
      globalSearchClearBtn.style.display = "none";
      closeGlobalSearch();
    });
  }

  if (globalSearchInput) {
    globalSearchInput.addEventListener("input", () => {
      const q = globalSearchInput.value.trim();
      if (globalSearchClearBtn) {
        globalSearchClearBtn.style.display = q ? "block" : "none";
      }

      clearTimeout(searchDebounceTimer);
      if (!q) {
        closeGlobalSearch();
        return;
      }

      searchDebounceTimer = setTimeout(async () => {
        try {
          const resp = await fetch(`/api/search/?q=${encodeURIComponent(q)}`);
          const data = await resp.json();
          if (data.ok) {
            renderGlobalSearchResults(data, q);
          }
        } catch (err) {
          console.error("Error en búsqueda global:", err);
        }
      }, 220);
    });

    globalSearchInput.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeGlobalSearch();
      }
    });
  }

  document.addEventListener("click", (e) => {
    const container = document.getElementById("globalSearchContainer");
    if (container && !container.contains(e.target)) {
      closeGlobalSearch();
    }
  });

  function renderGlobalSearchResults(data, query) {
    if (!globalSearchDropdown) return;

    let html = "";
    let hasAny = false;

    if (data.answer) {
      hasAny = true;
      html += `
        <div class="search-result-group search-ai-group">
          <div class="group-title">💡 Asistente UMSA</div>
          <div class="search-ai-bubble">${renderSimpleMarkdown(data.answer)}</div>
          <button type="button" class="btn btn-xs btn-outline mt-2 btn-search-to-chat">
            💬 Continuar en el Asistente
          </button>
        </div>
      `;
    }

    if (data.productos && data.productos.length > 0) {
      hasAny = true;
      html += `
        <div class="search-result-group">
          <div class="group-title">📦 Insumos & Insumos Médicos (${data.productos.length})</div>
          ${data.productos.map(p => `
            <div class="search-item search-item-product" data-name="${escapeHtml(p.producto)}">
              <div class="search-item-info">
                <strong>${escapeHtml(p.producto)}</strong>
                <span class="muted-text">${escapeHtml(p.presentacion || '')}</span>
              </div>
              <div class="search-item-meta">
                <span class="price-tag">$ ${Number(p.precio_unitario).toLocaleString("es-AR")}</span>
                <span class="badge badge-success">ILIMITADO</span>
              </div>
            </div>
          `).join("")}
        </div>
      `;
    }

    if (data.presupuestos && data.presupuestos.length > 0) {
      hasAny = true;
      html += `
        <div class="search-result-group">
          <div class="group-title">📋 Presupuestos Oficiales (${data.presupuestos.length})</div>
          ${data.presupuestos.map(p => `
            <div class="search-item search-item-presupuesto" data-numero="${escapeHtml(p.numero)}">
              <div class="search-item-info">
                <strong>${escapeHtml(p.numero)}</strong> · <span>${escapeHtml(p.cliente)}</span>
                <span class="muted-text">${escapeHtml(p.fecha || '')}</span>
              </div>
              <div class="search-item-meta">
                <span class="price-tag">${formatCurrency(p.total)}</span>
                <span class="badge ${p.estado === 'Confirmado' ? 'badge-success' : 'badge-warning'}">${escapeHtml(p.estado)}</span>
              </div>
            </div>
          `).join("")}
        </div>
      `;
    }

    if (!hasAny) {
      html = `<div class="search-no-results">No se encontraron resultados para "<b>${escapeHtml(query)}</b>".</div>`;
    }

    globalSearchDropdown.innerHTML = html;
    globalSearchDropdown.style.display = "block";

    // Asignar clics a resultados
    const chatJumpBtn = globalSearchDropdown.querySelector(".btn-search-to-chat");
    if (chatJumpBtn) {
      chatJumpBtn.addEventListener("click", () => {
        closeGlobalSearch();
        switchTab("tab-chat");
        if (chatInput) {
          chatInput.value = query;
          chatInput.focus();
        }
      });
    }

    globalSearchDropdown.querySelectorAll(".search-item-product").forEach(el => {
      el.addEventListener("click", () => {
        const prodName = el.getAttribute("data-name");
        closeGlobalSearch();
        switchTab("tab-chat");
        if (chatInput) {
          chatInput.value = `Quiero presupuestar ${prodName}`;
          if (chatForm) {
            chatForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
          }
        }
      });
    });

    globalSearchDropdown.querySelectorAll(".search-item-presupuesto").forEach(el => {
      el.addEventListener("click", () => {
        const num = el.getAttribute("data-numero");
        closeGlobalSearch();
        openPresupuestoDetail(num);
      });
    });
  }

  // =========================================================================
  // 17. HISTORIAL DE PRESUPUESTOS Y MODAL DETALLE
  // =========================================================================
  const historialTable = document.getElementById("historialTable");
  const historialTbody = document.getElementById("historialTbody");
  const historialSearchInput = document.getElementById("historialSearchInput");
  const historialDateFilter = document.getElementById("historialDateFilter");
  const btnRefreshHistorial = document.getElementById("btnRefreshHistorial");
  const btnHistorialNewBudget = document.getElementById("btnHistorialNewBudget");
  let activeHistorialFilter = "todos";

  document.querySelectorAll(".btn-group-filters .btn-filter").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".btn-group-filters .btn-filter").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeHistorialFilter = btn.getAttribute("data-filter") || "todos";
      loadHistorialPresupuestos();
    });
  });

  if (historialDateFilter) {
    historialDateFilter.addEventListener("change", () => {
      loadHistorialPresupuestos();
    });
  }

  if (historialSearchInput) {
    let histSearchTimer = null;
    historialSearchInput.addEventListener("input", () => {
      clearTimeout(histSearchTimer);
      histSearchTimer = setTimeout(() => {
        loadHistorialPresupuestos();
      }, 200);
    });
  }

  if (btnRefreshHistorial) {
    btnRefreshHistorial.addEventListener("click", loadHistorialPresupuestos);
  }

  if (btnHistorialNewBudget) {
    btnHistorialNewBudget.addEventListener("click", startBudgetFlow);
  }

  async function loadHistorialPresupuestos() {
    if (!historialTbody) return;
    const search = historialSearchInput ? historialSearchInput.value.trim() : "";
    const fecha = historialDateFilter ? historialDateFilter.value : "";
    const estado = activeHistorialFilter === "todos" ? "" : activeHistorialFilter;

    try {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (fecha) params.append("fecha", fecha);
      if (estado) params.append("estado", estado);

      const resp = await fetch(`/api/presupuestos/historial/?${params.toString()}`);
      const data = await resp.json();

      if (data.ok && Array.isArray(data.historial)) {
        if (data.historial.length === 0) {
          historialTbody.innerHTML = `<tr><td colspan="6" class="text-center muted-text py-4">No se encontraron presupuestos con los filtros seleccionados.</td></tr>`;
          return;
        }

        historialTbody.innerHTML = data.historial.map(p => {
          let badgeClass = "badge-subtle";
          if (p.estado === "Confirmado") badgeClass = "badge-success";
          else if (p.estado === "Pendiente") badgeClass = "badge-warning";
          else if (p.estado === "Cancelado") badgeClass = "badge-danger";

          return `
            <tr class="historial-row" data-numero="${escapeHtml(p.numero)}" data-cliente="${escapeHtml(p.cliente)}" data-estado="${escapeHtml(p.estado)}">
              <td><strong class="doc-num">${escapeHtml(p.numero)}</strong></td>
              <td>${escapeHtml(p.fecha)}</td>
              <td><strong class="client-name">${escapeHtml(p.cliente)}</strong></td>
              <td style="text-align: right; font-weight: 700; color: var(--primary-navy);">${formatCurrency(p.total)}</td>
              <td style="text-align: center;">
                <span class="badge badge-status ${badgeClass}">${escapeHtml(p.estado)}</span>
              </td>
              <td style="text-align: right;">
                <div class="action-buttons-inline">
                  <button type="button" class="btn btn-xs btn-outline btn-view-presupuesto" data-numero="${escapeHtml(p.numero)}" title="Ver detalle">
                    👁 Ver
                  </button>
                  <a href="${p.download_url}" class="btn btn-xs btn-outline" download="${escapeHtml(p.filename)}" title="Descargar PDF">
                    📄 PDF
                  </a>
                </div>
              </td>
            </tr>
          `;
        }).join("");

        attachHistorialRowEvents();
      }
    } catch (err) {
      console.error("Error al cargar historial:", err);
    }
  }

  function attachHistorialRowEvents() {
    document.querySelectorAll(".btn-view-presupuesto").forEach(b => {
      b.onclick = () => {
        const num = b.getAttribute("data-numero");
        openPresupuestoDetail(num);
      };
    });
  }

  // Modal Detalle de Presupuesto
  const presupuestoDetailModal = document.getElementById("presupuestoDetailModal");
  const detailModalCloseBtn = document.getElementById("detailModalCloseBtn");
  const detailModalCloseBtn2 = document.getElementById("detailModalCloseBtn2");
  const detailPresNumero = document.getElementById("detailPresNumero");
  const detailPresEstado = document.getElementById("detailPresEstado");
  const detailPresFecha = document.getElementById("detailPresFecha");
  const detailPresCliente = document.getElementById("detailPresCliente");
  const detailPresInstitucion = document.getElementById("detailPresInstitucion");
  const detailPresValidez = document.getElementById("detailPresValidez");
  const detailProductsTbody = document.getElementById("detailProductsTbody");
  const detailPresSubtotal = document.getElementById("detailPresSubtotal");
  const detailPresIvaLabel = document.getElementById("detailPresIvaLabel");
  const detailPresIva = document.getElementById("detailPresIva");
  const detailPresTotal = document.getElementById("detailPresTotal");
  const detailDownloadPdfBtn = document.getElementById("detailDownloadPdfBtn");

  function closePresupuestoModal() {
    if (presupuestoDetailModal) presupuestoDetailModal.style.display = "none";
  }

  if (detailModalCloseBtn) detailModalCloseBtn.onclick = closePresupuestoModal;
  if (detailModalCloseBtn2) detailModalCloseBtn2.onclick = closePresupuestoModal;
  if (presupuestoDetailModal) {
    presupuestoDetailModal.addEventListener("click", (e) => {
      if (e.target === presupuestoDetailModal) closePresupuestoModal();
    });
  }

  async function openPresupuestoDetail(numero) {
    if (!presupuestoDetailModal) return;
    try {
      const resp = await fetch(`/api/presupuestos/detail/?numero=${encodeURIComponent(numero)}`);
      const data = await resp.json();
      if (data.ok && data.presupuesto) {
        const p = data.presupuesto;
        if (detailPresNumero) detailPresNumero.textContent = p.numero;
        if (detailPresEstado) {
          detailPresEstado.textContent = p.estado;
          detailPresEstado.className = `badge ${p.estado === 'Confirmado' ? 'badge-success' : 'badge-warning'}`;
        }
        if (detailPresFecha) detailPresFecha.textContent = p.fecha || p.fecha_creacion || "-";
        if (detailPresCliente) detailPresCliente.textContent = p.cliente || "-";
        if (detailPresInstitucion) detailPresInstitucion.textContent = p.institucion || "-";
        if (detailPresValidez) detailPresValidez.textContent = p.validez || "15 días";

        if (detailProductsTbody) {
          const items = p.items || p.productos || [];
          if (items.length > 0) {
            detailProductsTbody.innerHTML = items.map(item => `
              <tr>
                <td><strong>${escapeHtml(item.descripcion)}</strong></td>
                <td style="text-align: center;">${item.cantidad}</td>
                <td style="text-align: right;">${formatCurrency(item.precio_unitario)}</td>
                <td style="text-align: right; font-weight: 700;">${formatCurrency(item.subtotal || (item.cantidad * item.precio_unitario))}</td>
              </tr>
            `).join("");
          } else {
            detailProductsTbody.innerHTML = `<tr><td colspan="4" class="text-center muted-text py-2">Sin productos especificados</td></tr>`;
          }
        }

        if (detailPresSubtotal) detailPresSubtotal.textContent = formatCurrency(p.subtotal);
        if (detailPresIvaLabel) detailPresIvaLabel.textContent = `IVA (${p.iva_porcentaje || 21}%):`;
        if (detailPresIva) detailPresIva.textContent = formatCurrency(p.iva_monto);
        if (detailPresTotal) detailPresTotal.textContent = formatCurrency(p.total);

        if (detailDownloadPdfBtn) {
          detailDownloadPdfBtn.href = p.download_url;
          detailDownloadPdfBtn.setAttribute("download", p.filename || `${p.numero}.pdf`);
        }

        presupuestoDetailModal.style.display = "flex";
      } else {
        alert("No se encontró el detalle del presupuesto.");
      }
    } catch (err) {
      alert("Error al cargar detalle: " + err.message);
    }
  }

  // =========================================================================
  // 18. BANNER DE BORRADOR ACTIVO EN CHAT
  // =========================================================================
  const chatDraftBanner = document.getElementById("chatDraftBanner");
  const chatDraftBannerText = document.getElementById("chatDraftBannerText");
  const btnConfirmDraftFromChat = document.getElementById("btnConfirmDraftFromChat");

  if (btnConfirmDraftFromChat) {
    btnConfirmDraftFromChat.addEventListener("click", () => {
      if (chatInput) {
        chatInput.value = "Confirmo";
        if (chatForm) {
          chatForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
        }
      }
    });
  }

  // Botón de refresco global
  const globalRefreshBtn = document.getElementById("globalRefreshBtn");
  if (globalRefreshBtn) {
    globalRefreshBtn.addEventListener("click", () => {
      refreshFilesList();
      loadMemory();
      loadHistory();
      loadModules();
      loadIndex();
      refreshPresupuestosList();
      refreshInventarioList();
      loadHistorialPresupuestos();
      refreshDashboardMetrics();
      alert("Sistema refrescado y sincronizado con files_storage/.");
    });
  }

  // =========================================================================
  // 19. MEDIOS DE PAGO Y GESTIÓN DE COBRANZAS
  // =========================================================================
  const kpiCobradoConfirmado = document.getElementById("kpiCobradoConfirmado");
  const kpiPendienteCobro = document.getElementById("kpiPendienteCobro");
  const kpiPagosCount = document.getElementById("kpiPagosCount");
  const kpiParcialesCount = document.getElementById("kpiParcialesCount");
  const mediosPagoGrid = document.getElementById("mediosPagoGrid");
  const btnRefreshPagos = document.getElementById("btnRefreshPagos");
  const btnOpenRegistrarPagoModal = document.getElementById("btnOpenRegistrarPagoModal");

  // Filtros de pagos
  const pagosTable = document.getElementById("pagosTable");
  const pagosTableCount = document.getElementById("pagosTableCount");
  const pagosSearchInput = document.getElementById("pagosSearchInput");
  const pagosFilterMedio = document.getElementById("pagosFilterMedio");
  const pagosFilterEstado = document.getElementById("pagosFilterEstado");
  const pagosFilterFecha = document.getElementById("pagosFilterFecha");
  const pagosOrderBy = document.getElementById("pagosOrderBy");
  const pagosClearFiltersBtn = document.getElementById("pagosClearFiltersBtn");

  // Modales
  const modalRegistrarPago = document.getElementById("modalRegistrarPago");
  const modalRegistrarPagoCloseBtn = document.getElementById("modalRegistrarPagoCloseBtn");
  const btnCancelRegistrarPago = document.getElementById("btnCancelRegistrarPago");
  const formRegistrarPago = document.getElementById("formRegistrarPago");
  const pagoPresupuestoSelect = document.getElementById("pagoPresupuestoSelect");
  const pagoPresupuestoInfoBox = document.getElementById("pagoPresupuestoInfoBox");
  const pagoClienteDisplay = document.getElementById("pagoClienteDisplay");
  const pagoTotalDisplay = document.getElementById("pagoTotalDisplay");
  const pagoYaPagadoDisplay = document.getElementById("pagoYaPagadoDisplay");
  const pagoSaldoPendienteDisplay = document.getElementById("pagoSaldoPendienteDisplay");
  const pagoClienteInput = document.getElementById("pagoClienteInput");
  const pagoInstitucionInput = document.getElementById("pagoInstitucionInput");
  const pagoFechaInput = document.getElementById("pagoFechaInput");
  const pagoMedioSelect = document.getElementById("pagoMedioSelect");
  const pagoImporteInput = document.getElementById("pagoImporteInput");
  const pagoEstadoSelect = document.getElementById("pagoEstadoSelect");
  const pagoOperacionInput = document.getElementById("pagoOperacionInput");
  const pagoObservacionesInput = document.getElementById("pagoObservacionesInput");
  const pagoExcedenteWrap = document.getElementById("pagoExcedenteWrap");
  const pagoPermitirExcedente = document.getElementById("pagoPermitirExcedente");

  const modalConfigMedio = document.getElementById("modalConfigMedio");
  const modalConfigMedioCloseBtn = document.getElementById("modalConfigMedioCloseBtn");
  const btnCancelConfigMedio = document.getElementById("btnCancelConfigMedio");
  const formConfigMedio = document.getElementById("formConfigMedio");
  const modalConfigMedioTitle = document.getElementById("modalConfigMedioTitle");
  const configMedioCodigo = document.getElementById("configMedioCodigo");
  const configMedioNombre = document.getElementById("configMedioNombre");
  const configMedioDescripcion = document.getElementById("configMedioDescripcion");
  const configMedioActivo = document.getElementById("configMedioActivo");
  const configMedioInstrucciones = document.getElementById("configMedioInstrucciones");
  const configMedioObservaciones = document.getElementById("configMedioObservaciones");
  const configBancariosSection = document.getElementById("configBancariosSection");
  const configMercadoPagoSection = document.getElementById("configMercadoPagoSection");

  const modalCancelarPago = document.getElementById("modalCancelarPago");
  const modalCancelarPagoCloseBtn = document.getElementById("modalCancelarPagoCloseBtn");
  const btnDismissCancelarPago = document.getElementById("btnDismissCancelarPago");
  const formCancelarPago = document.getElementById("formCancelarPago");
  const cancelPagoIdInput = document.getElementById("cancelPagoIdInput");
  const cancelPagoMotivoInput = document.getElementById("cancelPagoMotivoInput");
  const cancelPagoIdDisplay = document.getElementById("cancelPagoIdDisplay");
  const cancelPagoPresupuestoDisplay = document.getElementById("cancelPagoPresupuestoDisplay");
  const cancelPagoImporteDisplay = document.getElementById("cancelPagoImporteDisplay");

  const modalDetallePago = document.getElementById("modalDetallePago");
  const modalDetallePagoCloseBtn = document.getElementById("modalDetallePagoCloseBtn");
  const btnCerrarDetallePago = document.getElementById("btnCerrarDetallePago");
  const detallePagoModalTitle = document.getElementById("detallePagoModalTitle");
  const reciboBoxContent = document.getElementById("reciboBoxContent");

  let pagosSearchTimer = null;
  let cachedPagosList = [];

  function formatMoney(amount) {
    return Number(amount || 0).toLocaleString("es-AR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  async function refreshPagosSection() {
    await Promise.all([
      refreshPagosDashboardMetrics(),
      refreshMediosPagoGrid(),
      refreshPagosTable(),
      refreshPresupuestosOptionsInPagoSelect()
    ]);
  }

  async function refreshPagosDashboardMetrics() {
    try {
      const resp = await fetch("/api/pagos/dashboard/");
      const data = await resp.json();
      if (data.ok && data.metrics) {
        const m = data.metrics;
        if (kpiCobradoConfirmado) kpiCobradoConfirmado.textContent = `$ ${formatMoney(m.total_confirmado)}`;
        if (kpiPendienteCobro) kpiPendienteCobro.textContent = `$ ${formatMoney(m.total_pendiente_cobro)}`;
        if (kpiPagosCount) kpiPagosCount.textContent = m.cantidad_pagos_registrados || 0;
        if (kpiParcialesCount) kpiParcialesCount.textContent = m.cantidad_pagos_parciales || 0;
      }
    } catch (err) {
      console.error("Error al refrescar métricas de pagos:", err);
    }
  }

  async function refreshMediosPagoGrid() {
    if (!mediosPagoGrid) return;
    try {
      const resp = await fetch("/api/pagos/medios/");
      const data = await resp.json();
      if (data.ok && Array.isArray(data.medios)) {
        renderMediosPagoCards(data.medios);
        updateMedioSelectOptions(data.medios);
      }
    } catch (err) {
      console.error("Error al refrescar medios de pago:", err);
    }
  }

  function renderMediosPagoCards(medios) {
    if (!mediosPagoGrid) return;
    mediosPagoGrid.innerHTML = medios.map(medio => {
      let metaHtml = "";
      let brandTagsHtml = "";

      let logosStripHtml = "";
      if (medio.codigo === "tarjeta") {
        logosStripHtml = `
          <div class="medio-logos-strip">
            <img src="/static/img/medios/visa.svg" alt="Visa" title="Visa">
            <img src="/static/img/medios/mastercard.svg" alt="Mastercard" title="Mastercard">
            <img src="/static/img/medios/naranjax.svg" alt="Naranja X" title="Naranja X Plan Z">
            <img src="/static/img/medios/amex.svg" alt="Amex" title="American Express">
            <img src="/static/img/medios/cabal.svg" alt="Cabal" title="Cabal">
          </div>
        `;
        brandTagsHtml = `
          <div class="medio-brand-tags">
            <span class="mini-brand-tag tag-nx">Plan Z 3 Cuotas 0%</span>
            <span class="mini-brand-tag tag-cuotas">Cuota Simple 3 y 6</span>
            <span class="mini-brand-tag">Terminal POS</span>
          </div>
        `;
        metaHtml = `
          <div><strong>Terminal POS:</strong> Cobro presencial con chip, contactless y banda magnética.</div>
          <div class="text-muted">Habilitado para tarjetas de débito y crédito bancarias, Naranja X y Cuota Simple.</div>
        `;
      } else if (medio.codigo === "mercadopago") {
        logosStripHtml = `
          <div class="medio-logos-strip">
            <img src="/static/img/medios/mercadopago.svg" alt="Mercado Pago" title="Mercado Pago">
            <img src="/static/img/medios/modo.svg" alt="MODO" title="MODO Billeteras">
            <img src="/static/img/medios/uala.svg" alt="Ualá" title="Ualá">
          </div>
        `;
        brandTagsHtml = `
          <div class="medio-brand-tags">
            <span class="mini-brand-tag tag-mp">QR Dinámico</span>
            <span class="mini-brand-tag tag-bonif">15% OFF Dinero en Cuenta</span>
            <span class="mini-brand-tag tag-cuotas">Mercado Crédito</span>
          </div>
        `;
        const mp = medio.online_config || {};
        metaHtml = `
          <div><strong>Modo:</strong> Cobro con QR interoperable en mostrador y Link oficial.</div>
          <div class="text-muted"><em>📱 Acepta saldo en cuenta, tarjetas de crédito guardadas y transferencias vía CVU/Alias.</em></div>
          ${mp.link_pago_oficial ? `<div class="mt-1"><strong>Link:</strong> <span class="text-truncate">${escapeHtml(mp.link_pago_oficial)}</span></div>` : ""}
        `;
      } else if (medio.codigo === "transferencia") {
        logosStripHtml = `
          <div class="medio-logos-strip">
            <img src="/static/img/medios/transferencia.svg" alt="Transferencia CBU" title="Transferencia CBU">
            <img src="/static/img/medios/santander.svg" alt="Santander" title="Banco Santander">
            <img src="/static/img/medios/galicia.svg" alt="Galicia" title="Banco Galicia">
            <img src="/static/img/medios/bbva.svg" alt="BBVA" title="BBVA">
            <img src="/static/img/medios/cuentadni.svg" alt="Cuenta DNI" title="Cuenta DNI">
          </div>
        `;
        brandTagsHtml = `
          <div class="medio-brand-tags">
            <span class="mini-brand-tag tag-san">Santander Oficial</span>
            <span class="mini-brand-tag tag-bonif">10% OFF 24hs</span>
            <span class="mini-brand-tag">Alias Directo</span>
          </div>
        `;
        const b = medio.datos_bancarios || {};
        if (b.configurado) {
          metaHtml = `
            <div><strong>Banco:</strong> ${escapeHtml(b.banco || "-")}</div>
            <div><strong>CBU:</strong> <code>${escapeHtml(b.cbu || "-")}</code></div>
            <div><strong>Alias:</strong> <code>${escapeHtml(b.alias || "-")}</code></div>
            <div><strong>Titular:</strong> ${escapeHtml(b.titular || "-")}</div>
          `;
        } else {
          metaHtml = `<div class="text-muted"><em>🏛️ Datos bancarios oficiales: Banco Santander | Alias: <strong>UMSA.MEDICA.CENTRO</strong> | CBU: <code>0720234588000034567891</code></em></div>`;
        }
      } else {
        logosStripHtml = `
          <div class="medio-logos-strip">
            <img src="/static/img/medios/efectivo.svg" alt="Efectivo en Caja" title="Efectivo en Caja Central">
          </div>
        `;
        brandTagsHtml = `
          <div class="medio-brand-tags">
            <span class="mini-brand-tag tag-bonif">10% Bonificación Directa</span>
            <span class="mini-brand-tag">Ventanilla Central</span>
            <span class="mini-brand-tag">Recibo Oficial</span>
          </div>
        `;
        metaHtml = `
          <div><strong>Modalidad:</strong> Cobro presencial en ventanilla de caja administrativa.</div>
          <div class="text-muted">Emisión de recibo fiscal oficial al instante con 10% de bonificación directa.</div>
        `;
      }

      return `
        <div class="medio-pago-card ${!medio.activo ? "is-inactive" : ""}" data-codigo="${escapeHtml(medio.codigo)}">
          <div class="medio-card-header">
            <div class="medio-card-title-group">
              <div class="medio-card-icon">${escapeHtml(medio.icono || "💳")}</div>
              <div>
                <div class="medio-card-title">${escapeHtml(medio.nombre)}</div>
                <span class="text-muted" style="font-size: 11px;">Código: <code>${escapeHtml(medio.codigo)}</code></span>
              </div>
            </div>
            <div>
              <span class="badge ${medio.activo ? "badge-success" : "badge-subtle"}">
                ${medio.activo ? "Activo" : "Inactivo"}
              </span>
            </div>
          </div>

          <p class="medio-card-desc">${escapeHtml(medio.descripcion || "")}</p>
          ${logosStripHtml}
          ${brandTagsHtml}
          <div class="medio-card-meta-box">${metaHtml}</div>

          <div class="medio-card-actions">
            <button type="button" class="btn btn-xs btn-outline btn-config-medio"
                    data-codigo="${escapeHtml(medio.codigo)}"
                    data-nombre="${escapeHtml(medio.nombre)}"
                    data-descripcion="${escapeHtml(medio.descripcion || "")}"
                    data-activo="${medio.activo ? "1" : "0"}"
                    data-instrucciones="${escapeHtml(medio.instrucciones || "")}"
                    data-observaciones="${escapeHtml(medio.observaciones || "")}">
              ⚙️ Administrar
            </button>
            <button type="button" class="btn btn-xs ${medio.activo ? "btn-outline" : "btn-primary"} btn-toggle-medio"
                    data-codigo="${escapeHtml(medio.codigo)}"
                    data-activo="${medio.activo ? "1" : "0"}">
              ${medio.activo ? "Desactivar" : "Activar"}
            </button>
          </div>
        </div>
      `;
    }).join("");

    attachMediosCardsEvents();
  }

  function updateMedioSelectOptions(medios) {
    if (!pagoMedioSelect) return;
    const activeMedios = medios.filter(m => m.activo);
    pagoMedioSelect.innerHTML = activeMedios.map(m => `
      <option value="${escapeHtml(m.codigo)}">${escapeHtml(m.icono || "")} ${escapeHtml(m.nombre)}</option>
    `).join("");
  }

  function attachMediosCardsEvents() {
    if (!mediosPagoGrid) return;
    mediosPagoGrid.querySelectorAll(".btn-toggle-medio").forEach(btn => {
      btn.onclick = async () => {
        const codigo = btn.getAttribute("data-codigo");
        const currentActivo = btn.getAttribute("data-activo") === "1";
        try {
          btn.disabled = true;
          const resp = await fetch("/api/pagos/medios/toggle/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ codigo, activo: !currentActivo })
          });
          const data = await resp.json();
          if (data.ok) {
            await refreshMediosPagoGrid();
          } else {
            alert("Error al modificar estado: " + (data.error || ""));
          }
        } catch (e) {
          alert("Error de conexión al modificar medio de pago.");
        } finally {
          btn.disabled = false;
        }
      };
    });

    mediosPagoGrid.querySelectorAll(".btn-config-medio").forEach(btn => {
      btn.onclick = async () => {
        const codigo = btn.getAttribute("data-codigo");
        await openConfigMedioModal(codigo);
      };
    });
  }

  async function openConfigMedioModal(codigo) {
    if (!modalConfigMedio) return;
    try {
      const resp = await fetch("/api/pagos/medios/");
      const data = await resp.json();
      if (!data.ok) return;
      const medio = data.medios.find(m => m.codigo === codigo);
      if (!medio) return;

      if (modalConfigMedioTitle) modalConfigMedioTitle.textContent = `⚙️ Configurar: ${medio.nombre}`;
      if (configMedioCodigo) configMedioCodigo.value = medio.codigo;
      if (configMedioNombre) configMedioNombre.value = medio.nombre;
      if (configMedioDescripcion) configMedioDescripcion.value = medio.descripcion || "";
      if (configMedioActivo) configMedioActivo.checked = !!medio.activo;
      if (configMedioInstrucciones) configMedioInstrucciones.value = medio.instrucciones || "";
      if (configMedioObservaciones) configMedioObservaciones.value = medio.observaciones || "";

      // Bloque bancario
      if (configBancariosSection) {
        if (medio.codigo === "transferencia") {
          configBancariosSection.style.display = "block";
          const b = medio.datos_bancarios || {};
          const tInput = document.getElementById("configBancoTitular");
          const bInput = document.getElementById("configBancoNombre");
          const tcInput = document.getElementById("configBancoTipoCuenta");
          const ncInput = document.getElementById("configBancoNumeroCuenta");
          const cbuInput = document.getElementById("configBancoCbu");
          const alInput = document.getElementById("configBancoAlias");
          const cuitInput = document.getElementById("configBancoCuit");
          if (tInput) tInput.value = b.titular || "";
          if (bInput) bInput.value = b.banco || "";
          if (tcInput) tcInput.value = b.tipo_cuenta || "";
          if (ncInput) ncInput.value = b.numero_cuenta || "";
          if (cbuInput) cbuInput.value = b.cbu || "";
          if (alInput) alInput.value = b.alias || "";
          if (cuitInput) cuitInput.value = b.cuit || "";
        } else {
          configBancariosSection.style.display = "none";
        }
      }

      // Bloque Mercado Pago
      if (configMercadoPagoSection) {
        if (medio.codigo === "mercadopago") {
          configMercadoPagoSection.style.display = "block";
          const mp = medio.online_config || {};
          const lInput = document.getElementById("configMpLink");
          const aInput = document.getElementById("configMpAlias");
          const cvInput = document.getElementById("configMpCvu");
          if (lInput) lInput.value = mp.link_pago_oficial || "";
          if (aInput) aInput.value = mp.alias_mp || "";
          if (cvInput) cvInput.value = mp.cvu_mp || "";
        } else {
          configMercadoPagoSection.style.display = "none";
        }
      }

      modalConfigMedio.style.display = "flex";
    } catch (e) {
      alert("Error cargando configuración del medio de pago.");
    }
  }

  function closeConfigMedioModal() {
    if (modalConfigMedio) modalConfigMedio.style.display = "none";
  }

  if (modalConfigMedioCloseBtn) modalConfigMedioCloseBtn.onclick = closeConfigMedioModal;
  if (btnCancelConfigMedio) btnCancelConfigMedio.onclick = closeConfigMedioModal;
  if (modalConfigMedio) {
    modalConfigMedio.onclick = (e) => {
      if (e.target === modalConfigMedio) closeConfigMedioModal();
    };
  }

  if (formConfigMedio) {
    formConfigMedio.onsubmit = async (e) => {
      e.preventDefault();
      const codigo = configMedioCodigo ? configMedioCodigo.value : "";
      if (!codigo) return;

      const payload = {
        codigo: codigo,
        nombre: configMedioNombre ? configMedioNombre.value.trim() : "",
        descripcion: configMedioDescripcion ? configMedioDescripcion.value.trim() : "",
        activo: configMedioActivo ? configMedioActivo.checked : true,
        instrucciones: configMedioInstrucciones ? configMedioInstrucciones.value.trim() : "",
        observaciones: configMedioObservaciones ? configMedioObservaciones.value.trim() : "",
      };

      if (codigo === "transferencia") {
        payload.datos_bancarios = {
          titular: document.getElementById("configBancoTitular")?.value.trim() || "",
          banco: document.getElementById("configBancoNombre")?.value.trim() || "",
          tipo_cuenta: document.getElementById("configBancoTipoCuenta")?.value.trim() || "",
          numero_cuenta: document.getElementById("configBancoNumeroCuenta")?.value.trim() || "",
          cbu: document.getElementById("configBancoCbu")?.value.trim() || "",
          alias: document.getElementById("configBancoAlias")?.value.trim() || "",
          cuit: document.getElementById("configBancoCuit")?.value.trim() || "",
        };
      } else if (codigo === "mercadopago") {
        payload.online_config = {
          link_pago_oficial: document.getElementById("configMpLink")?.value.trim() || "",
          alias_mp: document.getElementById("configMpAlias")?.value.trim() || "",
          cvu_mp: document.getElementById("configMpCvu")?.value.trim() || "",
          gateway_status: "Pendiente de configuración",
        };
      }

      const btnSave = document.getElementById("btnSaveConfigMedio");
      const origText = btnSave ? btnSave.textContent : "";
      if (btnSave) {
        btnSave.disabled = true;
        btnSave.textContent = "⏳ Guardando...";
      }

      try {
        const resp = await fetch("/api/pagos/medios/save/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const resData = await resp.json();
        if (resData.ok) {
          closeConfigMedioModal();
          await refreshMediosPagoGrid();
        } else {
          alert("Error guardando medio de pago: " + (resData.error || ""));
        }
      } catch (err) {
        alert("Error de conexión al guardar configuración.");
      } finally {
        if (btnSave) {
          btnSave.disabled = false;
          btnSave.textContent = origText;
        }
      }
    };
  }

  // =========================================================================
  // TABLA DE HISTORIAL DE PAGOS & FILTROS
  // =========================================================================
  async function refreshPagosTable() {
    if (!pagosTable) return;
    const search = pagosSearchInput ? pagosSearchInput.value.trim() : "";
    const medio = pagosFilterMedio ? pagosFilterMedio.value.trim() : "";
    const estado = pagosFilterEstado ? pagosFilterEstado.value.trim() : "";
    const fecha = pagosFilterFecha ? pagosFilterFecha.value.trim() : "";
    const order = pagosOrderBy ? pagosOrderBy.value.trim() : "-fecha_pago";

    const q = new URLSearchParams({ search, medio, estado, fecha, order }).toString();
    try {
      const resp = await fetch(`/api/pagos/list/?${q}`);
      const data = await resp.json();
      if (data.ok && Array.isArray(data.pagos)) {
        cachedPagosList = data.pagos;
        if (pagosTableCount) pagosTableCount.textContent = `${data.pagos.length} registro${data.pagos.length === 1 ? "" : "s"}`;
        renderPagosTableRows(data.pagos);
      }
    } catch (e) {
      console.error("Error al refrescar listado de pagos:", e);
    }
  }

  function renderPagosTableRows(pagos) {
    if (!pagosTable) return;
    const tbody = pagosTable.querySelector("tbody");
    if (!tbody) return;

    if (pagos.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center muted-text py-4">No se encontraron pagos registrados coincidentes con los filtros.</td></tr>`;
      return;
    }

    tbody.innerHTML = pagos.map(p => {
      let badgeClass = "badge-pago-pagado";
      let badgeLabel = "Pagado";
      if (p.estado === "parcial") {
        badgeClass = "badge-pago-parcial";
        badgeLabel = "Parcial";
      } else if (p.estado === "pendiente") {
        badgeClass = "badge-pago-pendiente";
        badgeLabel = "Pendiente";
      } else if (p.estado === "cancelado") {
        badgeClass = "badge-pago-cancelado";
        badgeLabel = "Cancelado";
      }

      return `
        <tr class="pago-row" data-id="${p.id}">
          <td><span class="muted-text" style="font-size: 12.5px;">${escapeHtml(p.fecha_pago || "")}</span></td>
          <td>
            <strong style="color: var(--primary-navy); cursor: pointer;" class="link-to-presupuesto" data-numero="${escapeHtml(p.presupuesto_numero)}">
              ${escapeHtml(p.presupuesto_numero)}
            </strong>
          </td>
          <td>
            <strong>${escapeHtml(p.cliente || "")}</strong>
            ${p.institucion ? `<br/><span class="muted-text" style="font-size: 11px;">${escapeHtml(p.institucion)}</span>` : ""}
          </td>
          <td>
            <span>${escapeHtml(p.medio_pago_icono || "💳")} ${escapeHtml(p.medio_pago_nombre || "")}</span>
            ${p.numero_operacion ? `<br/><small class="muted-text">Ref: ${escapeHtml(p.numero_operacion)}</small>` : ""}
          </td>
          <td style="text-align: right; font-weight: 700; color: var(--primary-navy);">$ ${formatMoney(p.importe)}</td>
          <td style="text-align: center;"><span class="${badgeClass}">${badgeLabel}</span></td>
          <td style="text-align: right;">
            <div class="action-buttons-inline">
              <button type="button" class="btn btn-xs btn-outline btn-view-pago" data-id="${p.id}" title="Ver comprobante de pago">
                👁️
              </button>
              ${p.estado !== "cancelado" ? `
              <button type="button" class="btn btn-xs btn-danger-outline btn-cancel-pago" data-id="${p.id}" data-numero="${escapeHtml(p.presupuesto_numero)}" data-importe="${p.importe}" title="Cancelar pago">
                🚫
              </button>` : ""}
            </div>
          </td>
        </tr>
      `;
    }).join("");

    attachPagosTableEvents();
  }

  function attachPagosTableEvents() {
    if (!pagosTable) return;
    pagosTable.querySelectorAll(".btn-view-pago").forEach(btn => {
      btn.onclick = () => {
        const id = parseInt(btn.getAttribute("data-id"));
        openDetallePagoModal(id);
      };
    });

    pagosTable.querySelectorAll(".btn-cancel-pago").forEach(btn => {
      btn.onclick = () => {
        const id = btn.getAttribute("data-id");
        const num = btn.getAttribute("data-numero");
        const imp = btn.getAttribute("data-importe");
        openCancelarPagoModal(id, num, imp);
      };
    });

    pagosTable.querySelectorAll(".link-to-presupuesto").forEach(el => {
      el.onclick = () => {
        const num = el.getAttribute("data-numero");
        if (num) openPresupuestoDetail(num);
      };
    });
  }

  // Filtros de búsqueda reactivos
  if (pagosSearchInput) {
    pagosSearchInput.addEventListener("input", () => {
      clearTimeout(pagosSearchTimer);
      pagosSearchTimer = setTimeout(refreshPagosTable, 200);
    });
  }
  if (pagosFilterMedio) pagosFilterMedio.onchange = refreshPagosTable;
  if (pagosFilterEstado) pagosFilterEstado.onchange = refreshPagosTable;
  if (pagosFilterFecha) pagosFilterFecha.onchange = refreshPagosTable;
  if (pagosOrderBy) pagosOrderBy.onchange = refreshPagosTable;
  if (pagosClearFiltersBtn) {
    pagosClearFiltersBtn.onclick = () => {
      if (pagosSearchInput) pagosSearchInput.value = "";
      if (pagosFilterMedio) pagosFilterMedio.value = "";
      if (pagosFilterEstado) pagosFilterEstado.value = "";
      if (pagosFilterFecha) pagosFilterFecha.value = "";
      if (pagosOrderBy) pagosOrderBy.value = "-fecha_pago";
      refreshPagosTable();
    };
  }

  if (btnRefreshPagos) {
    btnRefreshPagos.onclick = refreshPagosSection;
  }

  // =========================================================================
  // MODAL REGISTRAR PAGO
  // =========================================================================
  async function refreshPresupuestosOptionsInPagoSelect() {
    if (!pagoPresupuestoSelect) return;
    try {
      const resp = await fetch("/api/presupuestos/historial/");
      const data = await resp.json();
      if (data.ok && Array.isArray(data.historial)) {
        const currentVal = pagoPresupuestoSelect.value;
        pagoPresupuestoSelect.innerHTML = `<option value="">-- Seleccione un presupuesto --</option>` +
          data.historial.map(pres => `
            <option value="${escapeHtml(pres.numero)}"
                    data-cliente="${escapeHtml(pres.cliente || '')}"
                    data-institucion="${escapeHtml(pres.institucion || '')}"
                    data-total="${pres.total || 0}"
                    data-pagado="${pres.total_pagado || 0}"
                    data-saldo="${pres.saldo_pendiente ?? pres.total}"
                    data-estado="${escapeHtml(pres.estado || '')}">
              ${escapeHtml(pres.numero)} - ${escapeHtml(pres.cliente)} ($ ${formatMoney(pres.total)} | Saldo: $ ${formatMoney(pres.saldo_pendiente ?? pres.total)})
            </option>
          `).join("");
        if (currentVal) pagoPresupuestoSelect.value = currentVal;
      }
    } catch (e) {
      console.error("Error al cargar presupuestos para registrar pago:", e);
    }
  }

  function openRegistrarPagoModal(preselectedNumero = null) {
    if (!modalRegistrarPago) return;
    if (pagoFechaInput) {
      pagoFechaInput.value = new Date().toISOString().split("T")[0];
    }
    if (pagoOperacionInput) pagoOperacionInput.value = "";
    if (pagoObservacionesInput) pagoObservacionesInput.value = "";
    if (pagoPermitirExcedente) pagoPermitirExcedente.checked = false;
    if (pagoExcedenteWrap) pagoExcedenteWrap.style.display = "none";

    refreshMediosPagoGrid();
    refreshPresupuestosOptionsInPagoSelect().then(() => {
      if (preselectedNumero && pagoPresupuestoSelect) {
        pagoPresupuestoSelect.value = preselectedNumero;
        pagoPresupuestoSelect.dispatchEvent(new Event("change"));
      }
    });

    modalRegistrarPago.style.display = "flex";
  }

  function closeRegistrarPagoModal() {
    if (modalRegistrarPago) modalRegistrarPago.style.display = "none";
  }

  if (btnOpenRegistrarPagoModal) {
    btnOpenRegistrarPagoModal.onclick = () => openRegistrarPagoModal(null);
  }
  if (modalRegistrarPagoCloseBtn) modalRegistrarPagoCloseBtn.onclick = closeRegistrarPagoModal;
  if (btnCancelRegistrarPago) btnCancelRegistrarPago.onclick = closeRegistrarPagoModal;
  if (modalRegistrarPago) {
    modalRegistrarPago.onclick = (e) => {
      if (e.target === modalRegistrarPago) closeRegistrarPagoModal();
    };
  }

  if (pagoPresupuestoSelect) {
    pagoPresupuestoSelect.addEventListener("change", () => {
      const opt = pagoPresupuestoSelect.selectedOptions[0];
      if (!opt || !opt.value) {
        if (pagoPresupuestoInfoBox) pagoPresupuestoInfoBox.style.display = "none";
        return;
      }

      const cliente = opt.getAttribute("data-cliente") || "";
      const institucion = opt.getAttribute("data-institucion") || "";
      const total = parseFloat(opt.getAttribute("data-total") || "0");
      const yaPagado = parseFloat(opt.getAttribute("data-pagado") || "0");
      const saldo = parseFloat(opt.getAttribute("data-saldo") || "0");

      if (pagoClienteDisplay) pagoClienteDisplay.textContent = cliente + (institucion ? ` (${institucion})` : "");
      if (pagoTotalDisplay) pagoTotalDisplay.textContent = `$ ${formatMoney(total)}`;
      if (pagoYaPagadoDisplay) pagoYaPagadoDisplay.textContent = `$ ${formatMoney(yaPagado)}`;
      if (pagoSaldoPendienteDisplay) pagoSaldoPendienteDisplay.textContent = `$ ${formatMoney(saldo)}`;

      if (pagoClienteInput) pagoClienteInput.value = cliente;
      if (pagoInstitucionInput) pagoInstitucionInput.value = institucion;

      if (pagoImporteInput) {
        pagoImporteInput.value = saldo > 0 ? saldo.toFixed(2) : "";
      }

      if (pagoPresupuestoInfoBox) pagoPresupuestoInfoBox.style.display = "block";
      checkSaldoExcedente();
    });
  }

  function checkSaldoExcedente() {
    if (!pagoPresupuestoSelect || !pagoImporteInput) return;
    const opt = pagoPresupuestoSelect.selectedOptions[0];
    if (!opt || !opt.value) return;
    const saldo = parseFloat(opt.getAttribute("data-saldo") || "0");
    const imp = parseFloat(pagoImporteInput.value || "0");
    if (imp > saldo && saldo > 0) {
      if (pagoExcedenteWrap) pagoExcedenteWrap.style.display = "block";
    } else {
      if (pagoExcedenteWrap) pagoExcedenteWrap.style.display = "none";
    }
  }

  if (pagoImporteInput) {
    pagoImporteInput.addEventListener("input", checkSaldoExcedente);
  }

  if (formRegistrarPago) {
    formRegistrarPago.onsubmit = async (e) => {
      e.preventDefault();
      const num = pagoPresupuestoSelect ? pagoPresupuestoSelect.value.trim() : "";
      if (!num) {
        alert("Debe seleccionar un presupuesto oficial.");
        return;
      }
      const imp = parseFloat(pagoImporteInput ? pagoImporteInput.value : "0");
      if (isNaN(imp) || imp <= 0) {
        alert("El importe abonado debe ser un número positivo mayor a 0.");
        return;
      }

      const payload = {
        presupuesto_numero: num,
        cliente: pagoClienteInput ? pagoClienteInput.value.trim() : "",
        institucion: pagoInstitucionInput ? pagoInstitucionInput.value.trim() : "",
        fecha_pago: pagoFechaInput ? pagoFechaInput.value : "",
        medio_pago: pagoMedioSelect ? pagoMedioSelect.value : "efectivo",
        importe: imp,
        estado: pagoEstadoSelect ? pagoEstadoSelect.value : "pagado",
        numero_operacion: pagoOperacionInput ? pagoOperacionInput.value.trim() : "",
        observaciones: pagoObservacionesInput ? pagoObservacionesInput.value.trim() : "",
        permitir_excedente: pagoPermitirExcedente ? pagoPermitirExcedente.checked : false,
      };

      const btnSubmit = document.getElementById("btnSubmitRegistrarPago");
      const origText = btnSubmit ? btnSubmit.textContent : "";
      if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.textContent = "⏳ Registrando...";
      }

      try {
        const resp = await fetch("/api/pagos/registrar/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await resp.json();
        if (data.ok) {
          closeRegistrarPagoModal();
          await refreshPagosSection();
          loadHistorialPresupuestos();
          refreshDashboardMetrics();
          alert(`✅ Pago registrado con éxito para el presupuesto ${num}. Saldo pendiente: $ ${formatMoney(data.presupuesto_summary?.saldo_pendiente)}`);
        } else {
          alert("Error al registrar pago: " + (data.error || ""));
        }
      } catch (err) {
        alert("Error de conexión al registrar pago.");
      } finally {
        if (btnSubmit) {
          btnSubmit.disabled = false;
          btnSubmit.textContent = origText;
        }
      }
    };
  }

  // =========================================================================
  // MODAL CANCELAR PAGO
  // =========================================================================
  function openCancelarPagoModal(id, num, imp) {
    if (!modalCancelarPago) return;
    if (cancelPagoIdInput) cancelPagoIdInput.value = id;
    if (cancelPagoIdDisplay) cancelPagoIdDisplay.textContent = `# ${id}`;
    if (cancelPagoPresupuestoDisplay) cancelPagoPresupuestoDisplay.textContent = num;
    if (cancelPagoImporteDisplay) cancelPagoImporteDisplay.textContent = `$ ${formatMoney(imp)}`;
    if (cancelPagoMotivoInput) cancelPagoMotivoInput.value = "";
    modalCancelarPago.style.display = "flex";
  }

  function closeCancelarPagoModal() {
    if (modalCancelarPago) modalCancelarPago.style.display = "none";
  }

  if (modalCancelarPagoCloseBtn) modalCancelarPagoCloseBtn.onclick = closeCancelarPagoModal;
  if (btnDismissCancelarPago) btnDismissCancelarPago.onclick = closeCancelarPagoModal;
  if (modalCancelarPago) {
    modalCancelarPago.onclick = (e) => {
      if (e.target === modalCancelarPago) closeCancelarPagoModal();
    };
  }

  if (formCancelarPago) {
    formCancelarPago.onsubmit = async (e) => {
      e.preventDefault();
      const id = cancelPagoIdInput ? parseInt(cancelPagoIdInput.value) : null;
      const motivo = cancelPagoMotivoInput ? cancelPagoMotivoInput.value.trim() : "";
      if (!id || !motivo) {
        alert("Debe indicar el motivo o justificación de la cancelación.");
        return;
      }

      const btnSubmit = document.getElementById("btnConfirmCancelarPago");
      if (btnSubmit) btnSubmit.disabled = true;

      try {
        const resp = await fetch("/api/pagos/cancelar/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pago_id: id, motivo: motivo })
        });
        const data = await resp.json();
        if (data.ok) {
          closeCancelarPagoModal();
          await refreshPagosSection();
          loadHistorialPresupuestos();
          refreshDashboardMetrics();
          alert(`Pago #${id} cancelado correctamente. Saldo actualizado del presupuesto: $ ${formatMoney(data.presupuesto_summary?.saldo_pendiente)}`);
        } else {
          alert("Error al cancelar pago: " + (data.error || ""));
        }
      } catch (err) {
        alert("Error de conexión al cancelar el pago.");
      } finally {
        if (btnSubmit) btnSubmit.disabled = false;
      }
    };
  }

  // =========================================================================
  // MODAL DETALLE / COMPROBANTE DE PAGO
  // =========================================================================
  function openDetallePagoModal(id) {
    if (!modalDetallePago || !reciboBoxContent) return;
    const pago = cachedPagosList.find(p => p.id === id);
    if (!pago) return;

    if (detallePagoModalTitle) detallePagoModalTitle.textContent = `🧾 Comprobante de Cobranza #${pago.id}`;

    let cancelHtml = "";
    if (pago.estado === "cancelado") {
      cancelHtml = `
        <div style="background:#fee2e2; border-left:3px solid #dc2626; padding:10px 14px; margin-top:12px; border-radius:4px;">
          <strong style="color:#b91c1c;">🚫 PAGO CANCELADO</strong>
          <p style="margin:4px 0 0; font-size:12px; color:#7f1d1d;"><strong>Motivo:</strong> ${escapeHtml(pago.motivo_cancelacion || "Sin justificación registrada")}</p>
          ${pago.fecha_cancelacion ? `<p style="margin:2px 0 0; font-size:11px; color:#991b1b;">Fecha de cancelación: ${escapeHtml(pago.fecha_cancelacion)}</p>` : ""}
        </div>
      `;
    }

    reciboBoxContent.innerHTML = `
      <div style="text-align:center; padding-bottom:12px; border-bottom:2px solid var(--primary-navy); margin-bottom:14px;">
        <h4 style="font-size:15px; font-weight:800; color:var(--primary-navy); margin-bottom:2px;">UMSA CENTRO MÉDICO</h4>
        <p style="font-size:11px; color:var(--text-muted); margin:0;">Comprobante Oficial de Cobranza · Sede Central</p>
      </div>

      <div class="recibo-row">
        <span>Número de Comprobante:</span>
        <strong># ${pago.id}</strong>
      </div>
      <div class="recibo-row">
        <span>Presupuesto Asociado:</span>
        <strong style="color:var(--primary-navy);">${escapeHtml(pago.presupuesto_numero)}</strong>
      </div>
      <div class="recibo-row">
        <span>Cliente / Profesional:</span>
        <strong>${escapeHtml(pago.cliente)}</strong>
      </div>
      ${pago.institucion ? `
      <div class="recibo-row">
        <span>Institución:</span>
        <span>${escapeHtml(pago.institucion)}</span>
      </div>` : ""}
      <div class="recibo-row">
        <span>Fecha de Pago:</span>
        <strong>${escapeHtml(pago.fecha_pago || "")}</strong>
      </div>
      <div class="recibo-row">
        <span>Medio de Pago:</span>
        <span>${escapeHtml(pago.medio_pago_icono || "💳")} ${escapeHtml(pago.medio_pago_nombre || "")}</span>
      </div>
      ${pago.numero_operacion ? `
      <div class="recibo-row">
        <span>N° Operación / Referencia:</span>
        <code>${escapeHtml(pago.numero_operacion)}</code>
      </div>` : ""}
      <div class="recibo-row">
        <span>Estado:</span>
        <span><strong>${escapeHtml(pago.estado_display || pago.estado)}</strong></span>
      </div>
      <div class="recibo-row highlight">
        <span>IMPORTE ABONADO:</span>
        <span>$ ${formatMoney(pago.importe)}</span>
      </div>

      ${pago.observaciones ? `
      <div style="margin-top:10px; font-size:12px; color:var(--text-muted);">
        <strong>Observaciones:</strong> ${escapeHtml(pago.observaciones)}
      </div>` : ""}

      ${cancelHtml}

      <div style="margin-top:14px; text-align:right; font-size:10.5px; color:var(--text-light);">
        Registrado en el sistema: ${escapeHtml(pago.created_at || "")}
      </div>
    `;

    modalDetallePago.style.display = "flex";
  }

  function closeDetallePagoModal() {
    if (modalDetallePago) modalDetallePago.style.display = "none";
  }

  if (modalDetallePagoCloseBtn) modalDetallePagoCloseBtn.onclick = closeDetallePagoModal;
  if (btnCerrarDetallePago) btnCerrarDetallePago.onclick = closeDetallePagoModal;
  if (modalDetallePago) {
    modalDetallePago.onclick = (e) => {
      if (e.target === modalDetallePago) closeDetallePagoModal();
    };
  }

  // =========================================================================
  // SIMULADOR DE CUOTAS Y PLANES DE FINANCIACIÓN
  // =========================================================================
  const simuladorMontoInput = document.getElementById("simuladorMontoInput");
  const simuladorTarjetaSelect = document.getElementById("simuladorTarjetaSelect");
  const btnCopiarSimulacion = document.getElementById("btnCopiarSimulacion");
  const quickAmountBtns = document.querySelectorAll(".btn-quick-amount");

  function recalculateCuotas() {
    if (!simuladorMontoInput) return;
    const monto = Math.max(100, parseFloat(simuladorMontoInput.value) || 0);
    const entidad = simuladorTarjetaSelect ? simuladorTarjetaSelect.value : "naranjax";

    // 1 Pago
    const resCuota1 = document.getElementById("resCuota1");
    const resTotal1 = document.getElementById("resTotal1");
    if (resCuota1) resCuota1.textContent = `$ ${formatMoney(monto)}`;
    if (resTotal1) {
      const conDescuento = monto * 0.9;
      resTotal1.innerHTML = `Total: $${formatMoney(monto)} • <strong>$${formatMoney(conDescuento)}</strong> con Efectivo/Transferencia (10% OFF)`;
    }

    // 3 Cuotas
    const resCuota3 = document.getElementById("resCuota3");
    const resTotal3 = document.getElementById("resTotal3");
    const resDetalle3 = document.getElementById("resDetalle3");
    const cuota3Val = monto / 3;
    if (resCuota3) resCuota3.textContent = `3 x $ ${formatMoney(cuota3Val)}`;
    if (resTotal3) resTotal3.textContent = `Total financiado: $${formatMoney(monto)} (CFT: 0,00% · TNA: 0,00%)`;
    if (resDetalle3) {
      if (entidad === "naranjax") {
        resDetalle3.innerHTML = `• <strong>Plan Z</strong> Naranja X: 3 cuotas cero interés.<br/>• 10% OFF en primera cotización.`;
      } else if (entidad === "santander") {
        resDetalle3.innerHTML = `• <strong>Santander</strong>: 3 cuotas sin interés en insumos.<br/>• 15% de reintegro los martes.`;
      } else if (entidad === "galicia") {
        resDetalle3.innerHTML = `• <strong>Galicia</strong>: 3 cuotas sin interés con Visa/Master.<br/>• 20% ahorro los jueves con MODO.`;
      } else if (entidad === "mercadopago") {
        resDetalle3.innerHTML = `• <strong>Mercado Pago</strong>: 3 cuotas con tarjetas bancarias.<br/>• O 10% OFF pagando con saldo en cuenta.`;
      } else {
        resDetalle3.innerHTML = `• <strong>Cuota Simple</strong>: 3 cuotas sin recargo bancario.<br/>• Tarjetas Visa y Mastercard de todos los bancos.`;
      }
    }

    // 6 Cuotas
    const resCuota6 = document.getElementById("resCuota6");
    const resTotal6 = document.getElementById("resTotal6");
    const factor6 = (entidad === "santander") ? 1.0 : 1.14;
    const cuota6Val = (monto * factor6) / 6;
    if (resCuota6) resCuota6.textContent = `6 x $ ${formatMoney(cuota6Val)}`;
    if (resTotal6) {
      if (factor6 === 1.0) {
        resTotal6.textContent = `Total financiado: $${formatMoney(monto)} (Promoción Santander 6 Sin Interés)`;
      } else {
        resTotal6.textContent = `Total financiado: $${formatMoney(monto * factor6)} (TNA: 28,00%)`;
      }
    }

    // 12 Cuotas
    const resCuota12 = document.getElementById("resCuota12");
    const resTotal12 = document.getElementById("resTotal12");
    const factor12 = 1.32;
    const cuota12Val = (monto * factor12) / 12;
    if (resCuota12) resCuota12.textContent = `12 x $ ${formatMoney(cuota12Val)}`;
    if (resTotal12) resTotal12.textContent = `Total financiado: $${formatMoney(monto * factor12)} (TNA: 32,00%)`;
  }

  function initCuotasSimulator() {
    if (simuladorMontoInput) {
      simuladorMontoInput.addEventListener("input", recalculateCuotas);
    }
    if (simuladorTarjetaSelect) {
      simuladorTarjetaSelect.addEventListener("change", recalculateCuotas);
    }
    quickAmountBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        quickAmountBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        if (simuladorMontoInput) {
          simuladorMontoInput.value = btn.getAttribute("data-monto");
          recalculateCuotas();
        }
      });
    });

    document.querySelectorAll(".btn-use-promo").forEach(btn => {
      btn.addEventListener("click", () => {
        const desc = btn.getAttribute("data-desc") || "";
        if (simuladorTarjetaSelect) {
          if (desc.includes("Naranja")) simuladorTarjetaSelect.value = "naranjax";
          else if (desc.includes("Santander")) simuladorTarjetaSelect.value = "santander";
          else if (desc.includes("Galicia")) simuladorTarjetaSelect.value = "galicia";
          else if (desc.includes("Mercado")) simuladorTarjetaSelect.value = "mercadopago";
          else simuladorTarjetaSelect.value = "bancaria";
          recalculateCuotas();
        }
        const simPane = document.querySelector(".cuotas-simulator-wrap");
        if (simPane) {
          simPane.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      });
    });

    if (btnCopiarSimulacion) {
      btnCopiarSimulacion.addEventListener("click", () => {
        const monto = parseFloat(simuladorMontoInput.value) || 0;
        const entidad = simuladorTarjetaSelect ? simuladorTarjetaSelect.options[simuladorTarjetaSelect.selectedIndex].text : "Naranja X / Bancaria";
        const text = `🏥 *Planes de Financiación - UMSA Centro Médico*\n` +
          `• Monto Base: $${formatMoney(monto)}\n` +
          `• Entidad / Tarjeta: ${entidad}\n` +
          `• 1 Pago (Efectivo / Transferencia): $${formatMoney(monto * 0.9)} (10% OFF Contado)\n` +
          `• 3 Cuotas Sin Interés: 3 pagos de $${formatMoney(monto / 3)} (Total $${formatMoney(monto)})\n` +
          `• 6 Cuotas: 6 pagos de $${formatMoney((monto * 1.14) / 6)} (Total $${formatMoney(monto * 1.14)})\n` +
          `Cobros y cotizaciones oficiales en administración UMSA.`;
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(() => {
            alert("Resumen de cuotas copiado al portapapeles.");
          }).catch(() => {
            prompt("Copiá el resumen:", text);
          });
        } else {
          prompt("Copiá el resumen:", text);
        }
      });
    }

    recalculateCuotas();
  }

  function initPagosBannersAndFilters() {
    // 1. CAROUSEL DE BANNERS
    const track = document.getElementById("pagosBannersTrack");
    const slider = document.getElementById("pagosBannersSlider");
    const prevBtn = document.getElementById("btnBannerPrev");
    const nextBtn = document.getElementById("btnBannerNext");
    const dots = document.querySelectorAll("#bannerDotsWrap .banner-dot");
    let currentSlide = 0;
    const totalSlides = 3;
    let autoSlideInterval = null;

    function goToSlide(idx) {
      if (idx < 0) currentSlide = totalSlides - 1;
      else if (idx >= totalSlides) currentSlide = 0;
      else currentSlide = idx;

      if (track) {
        track.style.transform = `translateX(-${currentSlide * 100}%)`;
      }
      dots.forEach((dot, i) => {
        dot.classList.toggle("active", i === currentSlide);
      });
    }

    if (prevBtn) prevBtn.onclick = () => { goToSlide(currentSlide - 1); resetAutoSlide(); };
    if (nextBtn) nextBtn.onclick = () => { goToSlide(currentSlide + 1); resetAutoSlide(); };

    dots.forEach(dot => {
      dot.onclick = () => {
        const slideIdx = parseInt(dot.getAttribute("data-slide"), 10) || 0;
        goToSlide(slideIdx);
        resetAutoSlide();
      };
    });

    function startAutoSlide() {
      stopAutoSlide();
      autoSlideInterval = setInterval(() => {
        goToSlide(currentSlide + 1);
      }, 6500);
    }

    function stopAutoSlide() {
      if (autoSlideInterval) {
        clearInterval(autoSlideInterval);
        autoSlideInterval = null;
      }
    }

    function resetAutoSlide() {
      startAutoSlide();
    }

    if (slider) {
      slider.onmouseenter = stopAutoSlide;
      slider.onmouseleave = startAutoSlide;
      startAutoSlide();
    }

    // 2. BOTONES DENTRO DE LOS BANNERS
    document.querySelectorAll(".btn-banner-simular").forEach(btn => {
      btn.onclick = () => {
        const tarjeta = btn.getAttribute("data-tarjeta") || "naranjax";
        if (simuladorTarjetaSelect) {
          if (tarjeta === "naranjax") simuladorTarjetaSelect.value = "naranjax";
          else if (tarjeta === "mercadopago") simuladorTarjetaSelect.value = "mercadopago";
          else if (tarjeta === "santander") simuladorTarjetaSelect.value = "santander";
          else if (tarjeta === "galicia") simuladorTarjetaSelect.value = "galicia";
          else simuladorTarjetaSelect.value = "bancaria";
          recalculateCuotas();
        }
        const simWrap = document.querySelector(".cuotas-simulator-wrap");
        if (simWrap) {
          simWrap.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      };
    });

    document.querySelectorAll(".btn-banner-copiar").forEach(btn => {
      btn.onclick = () => {
        const promoCode = btn.getAttribute("data-promo") || "PLANZ-UMSA";
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(promoCode).then(() => {
            alert(`✅ Cupón promocional '${promoCode}' copiado al portapapeles. ¡Presentalo en caja para validar tus beneficios!`);
          }).catch(() => {
            prompt("Copiá tu cupón promocional:", promoCode);
          });
        } else {
          prompt("Copiá tu cupón promocional:", promoCode);
        }
      };
    });

    // 3. TARJETAS DE MARCAS EN EL SHOWCASE (Click interactivo hacia el simulador)
    document.querySelectorAll(".medios-brands-grid .medio-brand-card").forEach(card => {
      card.onclick = () => {
        const medioKey = card.getAttribute("data-medio") || "";
        if (simuladorTarjetaSelect) {
          if (medioKey === "naranjax") simuladorTarjetaSelect.value = "naranjax";
          else if (medioKey === "santander") simuladorTarjetaSelect.value = "santander";
          else if (medioKey === "galicia") simuladorTarjetaSelect.value = "galicia";
          else if (medioKey === "mercadopago") simuladorTarjetaSelect.value = "mercadopago";
          else simuladorTarjetaSelect.value = "bancaria";
          recalculateCuotas();
        }
        const simWrap = document.querySelector(".cuotas-simulator-wrap");
        if (simWrap) {
          simWrap.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      };
    });

    // 4. FILTROS DE PROMOCIONES
    const promoFilterBtns = document.querySelectorAll("#promosFilterBar .promo-filter-btn");
    const promoCards = document.querySelectorAll("#promocionesGrid .promo-card");

    promoFilterBtns.forEach(btn => {
      btn.onclick = () => {
        promoFilterBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        const targetCat = btn.getAttribute("data-category") || "todas";
        promoCards.forEach(card => {
          const cardCat = card.getAttribute("data-category") || "";
          if (targetCat === "todas" || cardCat.includes(targetCat)) {
            card.style.display = "flex";
            card.style.opacity = "1";
          } else {
            card.style.display = "none";
          }
        });
      };
    });

    // Botones para filtrar promos desde banners
    document.querySelectorAll(".btn-filter-promos-btn").forEach(btn => {
      btn.onclick = () => {
        const targetCat = btn.getAttribute("data-category") || "todas";
        const matchingBtn = document.querySelector(`#promosFilterBar .promo-filter-btn[data-category="${targetCat}"]`);
        if (matchingBtn) {
          matchingBtn.click();
        }
        const promoSec = document.getElementById("seccionPromociones");
        if (promoSec) {
          promoSec.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      };
    });
  }

  // Activar eventos de botones de la tabla pre-renderizada por el servidor
  attachMediosCardsEvents();
  attachPagosTableEvents();

  // Inicializaciones
  recalculateBudgetTotals();
  refreshPresupuestosList();
  loadHistorialPresupuestos();
  refreshDashboardMetrics();
  attachHistorialRowEvents();
  initCuotasSimulator();
  initPagosBannersAndFilters();

});

