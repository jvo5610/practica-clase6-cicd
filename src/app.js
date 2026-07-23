export const stages = [
  { title: "Código", description: "Un cambio entra al repositorio." },
  { title: "Validación", description: "Lint y tests revisan el cambio." },
  { title: "Construcción", description: "Se genera un artefacto reproducible." },
  { title: "Paquete", description: "Docker verifica una entrega portable." },
  { title: "Despliegue", description: "GitHub Pages publica el resultado." }
];

export function calculateProgress(completed, total) {
  if (!Number.isInteger(completed) || !Number.isInteger(total) || total <= 0) {
    throw new TypeError("completed y total deben ser enteros válidos");
  }

  const safeCompleted = Math.min(Math.max(completed, 0), total);
  return Math.round((safeCompleted / total) * 100);
}

export function getStatusMessage(completed, total) {
  if (completed === 0) {
    return "El pipeline está listo para comenzar.";
  }

  if (completed >= total) {
    return "¡Entrega completada! El cambio llegó a producción.";
  }

  return `${completed} de ${total} controles completados.`;
}

const storageKey = "formatec-cicd-stages";

function loadCompletedStages() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) ?? "[]");
    return Array.isArray(saved) ? saved.filter(Number.isInteger) : [];
  } catch {
    return [];
  }
}

function initializeApp() {
  const pipeline = document.querySelector("#pipeline");
  const template = document.querySelector("#stage-template");
  const resetButton = document.querySelector("#reset-button");
  const completedStages = new Set(loadCompletedStages());

  function updateProgress() {
    const completed = completedStages.size;
    const percentage = calculateProgress(completed, stages.length);
    const progressBar = document.querySelector("#progress-bar");
    const progressTrack = document.querySelector('[role="progressbar"]');

    document.querySelector("#percentage").textContent = `${percentage}%`;
    document.querySelector("#status").textContent = getStatusMessage(
      completed,
      stages.length
    );
    progressBar.style.width = `${percentage}%`;
    progressTrack.setAttribute("aria-valuenow", String(percentage));
    localStorage.setItem(storageKey, JSON.stringify([...completedStages]));
  }

  stages.forEach((stage, index) => {
    const fragment = template.content.cloneNode(true);
    const input = fragment.querySelector("input");

    fragment.querySelector(".stage-number").textContent = String(index + 1);
    fragment.querySelector(".stage-title").textContent = stage.title;
    fragment.querySelector(".stage-description").textContent =
      stage.description;
    input.checked = completedStages.has(index);
    input.setAttribute("aria-label", `Completar etapa ${stage.title}`);

    input.addEventListener("change", () => {
      if (input.checked) {
        completedStages.add(index);
      } else {
        completedStages.delete(index);
      }
      updateProgress();
    });

    pipeline.append(fragment);
  });

  resetButton.addEventListener("click", () => {
    completedStages.clear();
    document
      .querySelectorAll('#pipeline input[type="checkbox"]')
      .forEach((input) => {
        input.checked = false;
      });
    updateProgress();
  });

  updateProgress();
}

if (typeof document !== "undefined") {
  initializeApp();
}

