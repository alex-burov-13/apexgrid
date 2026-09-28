function partsUntil(target) {
  const remaining = Math.max(0, target.getTime() - Date.now());
  const totalSeconds = Math.floor(remaining / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return [days, hours, minutes, seconds].map((value) => String(value).padStart(2, "0"));
}

export function initCountdowns() {
  const counters = [...document.querySelectorAll("[data-countdown]")]
    .map((element) => ({
      element,
      output: element.querySelector("[data-countdown-value]"),
      target: new Date(element.dataset.target),
    }))
    .filter(({ output, target }) => output && !Number.isNaN(target.getTime()));

  if (!counters.length) return;

  const render = () => {
    for (const { output, target } of counters) {
      output.textContent = partsUntil(target).join(":");
    }
  };
  render();
  window.setInterval(render, 1000);
}
