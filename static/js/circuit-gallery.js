export function initCircuitSearch() {
  const input = document.querySelector("[data-circuit-search]");
  const cards = [...document.querySelectorAll("[data-circuit-card]")];
  const empty = document.querySelector("[data-circuit-empty]");
  if (!input || !cards.length) return;

  input.addEventListener("input", () => {
    const query = input.value.trim().toLocaleLowerCase("ru");
    let visible = 0;
    for (const card of cards) {
      const matches = !query || card.dataset.search.toLocaleLowerCase("ru").includes(query);
      card.hidden = !matches;
      if (matches) visible += 1;
    }
    if (empty) empty.hidden = visible !== 0;
  });
}
