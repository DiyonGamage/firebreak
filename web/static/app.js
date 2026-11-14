const atmosphere = document.querySelector("#atmosphere");
const o2 = document.querySelector("#o2");
const pressure = document.querySelector("#pressure");

function syncAtmosphere() {
  if (!atmosphere || !o2 || !pressure) return;
  const option = atmosphere.selectedOptions[0];
  if (!option || option.dataset.custom === "true") return;
  if (option.dataset.o2) o2.value = option.dataset.o2;
  if (option.dataset.pressure) pressure.value = option.dataset.pressure;
}

atmosphere?.addEventListener("change", syncAtmosphere);

document.querySelector("#print")?.addEventListener("click", () => window.print());

document.querySelector("#copy-link")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    await navigator.clipboard.writeText(window.location.href);
    const original = button.textContent;
    button.textContent = "Copied";
    setTimeout(() => {
      button.textContent = original;
    }, 1400);
  } catch {
    button.textContent = "Copy failed";
  }
});

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("in");
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.06 }
);

document.querySelectorAll(".panel, .grade-card, .stat").forEach((element) => {
  element.classList.add("reveal");
  observer.observe(element);
});

const assistantForm = document.querySelector("#assistant-form");
const assistantQuery = document.querySelector("#assistant-query");
const assistantAnswer = document.querySelector("#assistant-answer");
const assistantTrace = document.querySelector("#assistant-trace");

assistantForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = assistantQuery?.value.trim();
  if (!query) return;
  assistantAnswer.hidden = false;
  assistantAnswer.textContent = "Routing local evidence tools…";
  assistantTrace.hidden = true;
  try {
    const response = await fetch(
      `/api/assistant?q=${encodeURIComponent(query)}&engine=${document.querySelector("#assistant-cactus")?.checked ? "cactus" : "fallback"}`
    );
    const payload = await response.json();
    assistantAnswer.textContent = payload.answer || "No answer returned.";
    const trace = (payload.trace || [])
      .map((item) => `${item.name}(${JSON.stringify(item.arguments)})`)
      .join("\n");
    if (trace) {
      assistantTrace.hidden = false;
      assistantTrace.textContent = `engine: ${payload.engine}\n${trace}`;
    } else if (payload.engine) {
      assistantTrace.hidden = false;
      assistantTrace.textContent = `engine: ${payload.engine}`;
    }
  } catch {
    assistantAnswer.textContent = "The local router is unavailable. Use the evidence ledger or JSON endpoint.";
  }
});

