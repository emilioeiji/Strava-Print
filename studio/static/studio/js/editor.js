const form = document.querySelector("#editor-form");
const overlay = document.querySelector("#processing-overlay");
const errors = document.querySelector("#form-errors");
const saveState = document.querySelector("#save-state");
const previewImage = document.querySelector("#preview-image");
const previewFrame = document.querySelector("#preview-frame");
let zoom = 1;

document.querySelectorAll("[data-tab]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-tab]").forEach((item) => item.classList.remove("is-active"));
    document.querySelectorAll("[data-panel]").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    document.querySelector(`[data-panel="${button.dataset.tab}"]`).classList.add("is-active");
  });
});

document.querySelectorAll("[data-zoom]").forEach((button) => {
  button.addEventListener("click", () => {
    zoom = Math.min(1.4, Math.max(0.6, zoom + (button.dataset.zoom === "in" ? 0.1 : -0.1)));
    previewFrame.style.transform = `scale(${zoom})`;
    document.querySelector("#zoom-value").textContent = `${Math.round(zoom * 100)}%`;
  });
});

document.querySelectorAll("input[type=range]").forEach((input) => {
  input.addEventListener("input", () => {
    const output = document.querySelector(`[data-output-for="${input.id}"]`);
    if (output) output.textContent = input.value;
  });
});

function showErrors(payload) {
  const messages = [];
  if (payload.error) messages.push(payload.error);
  if (payload.errors) {
    Object.entries(payload.errors).forEach(([field, fieldErrors]) => {
      messages.push(`${field}: ${fieldErrors.join(" ")}`);
    });
  }
  errors.innerHTML = messages.map((message) => `<div>${message}</div>`).join("");
  errors.hidden = messages.length === 0;
}

function updateMetrics(metrics) {
  const grid = document.querySelector("#metric-grid");
  grid.innerHTML = metrics.map((metric) => `
    <div class="metric-item"><span>${metric.label}</span><strong>${metric.value}</strong><small>${metric.unit}</small></div>
  `).join("");
}

function updateDownloads(artifacts) {
  const container = document.querySelector("#downloads");
  const heading = container.querySelector(".section-heading").outerHTML;
  container.innerHTML = heading + artifacts.map((artifact) => {
    const size = artifact.size > 1024 * 1024 ? `${(artifact.size / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(artifact.size / 1024)} KB`;
    return `<a class="download-row" href="${artifact.url}"><span>${artifact.label}</span><small>${size}</small></a>`;
  }).join("");
}

async function pollJob(url) {
  for (let attempt = 0; attempt < 150; attempt += 1) {
    const response = await fetch(url, {headers: {"X-Requested-With": "XMLHttpRequest"}});
    const payload = await response.json();
    saveState.textContent = `${payload.status} ${payload.progress || 0}%`;
    if (payload.job_status === "complete") {
      updateDownloads(payload.artifacts);
      return payload;
    }
    if (payload.job_status === "failed") throw new Error(payload.error || "A exportação falhou.");
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error("A exportação continua na fila. Consulte novamente em alguns minutos.");
}

async function submitAction(action) {
  overlay.hidden = false;
  errors.hidden = true;
  saveState.textContent = action === "export" ? "GERANDO" : "ATUALIZANDO";
  try {
    const response = await fetch(form.dataset[action + "Url"], {
      method: "POST",
      body: new FormData(form),
      headers: {"X-Requested-With": "XMLHttpRequest"},
    });
    const payload = await response.json();
    if (!response.ok) {
      showErrors(payload);
      saveState.textContent = "REVISAR";
      return;
    }
    if (payload.preview_url && previewImage) {
      previewImage.src = `${payload.preview_url}?v=${Date.now()}`;
      updateMetrics(payload.metrics);
    }
    if (payload.job_url && payload.job_status !== "complete") {
      const completed = await pollJob(payload.job_url);
      payload.status = completed.status;
    } else if (payload.artifacts) {
      updateDownloads(payload.artifacts);
    }
    saveState.textContent = payload.status || "SALVO";
  } catch (error) {
    showErrors({error: "Não foi possível concluir a operação. Verifique o servidor e tente novamente."});
    saveState.textContent = "ERRO";
  } finally {
    overlay.hidden = true;
  }
}

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => submitAction(button.dataset.action));
});
