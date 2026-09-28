import { postForm } from "./preferences.js";

function cardMatches(card, filter) {
  if (filter === "all") return true;
  if (filter === "sprint") return card.dataset.sprint === "true";
  const race = card.querySelector('time[data-session-type="race"]');
  if (!race) return false;
  const startsAt = new Date(race.dataset.utc).getTime();
  const endsAt = startsAt + 3 * 60 * 60 * 1000;
  const completed = endsAt <= Date.now();
  return filter === "completed" ? completed : startsAt > Date.now();
}

function initFilters() {
  const buttons = [...document.querySelectorAll("[data-calendar-filter]")];
  const cards = [...document.querySelectorAll("[data-event-card]")];
  const empty = document.querySelector("[data-calendar-empty]");
  if (!buttons.length || !cards.length) return;

  for (const button of buttons) {
    button.addEventListener("click", () => {
      const filter = button.dataset.calendarFilter;
      let visible = 0;
      for (const card of cards) {
        const matches = cardMatches(card, filter);
        card.hidden = !matches;
        if (matches) visible += 1;
      }
      for (const candidate of buttons) {
        candidate.setAttribute("aria-pressed", String(candidate === button));
      }
      if (empty) empty.hidden = visible !== 0;
    });
  }
}

function initViewSwitch() {
  const form = document.querySelector("[data-calendar-view-form]");
  if (!form) return;
  const input = form.querySelector('input[name="view"]');
  const buttons = [...form.querySelectorAll("[data-calendar-view]")];
  for (const button of buttons) {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      const view = button.dataset.calendarView;
      input.value = view;
      document.body.dataset.calendarView = view;
      for (const candidate of buttons) {
        candidate.setAttribute("aria-pressed", String(candidate === button));
      }
      try {
        const formData = new FormData(form);
        formData.set("view", view);
        await postForm(form, formData);
      } catch (_) {
        form.submit();
      }
    });
  }
}

export function initCalendarFilters() {
  initFilters();
  initViewSwitch();
}
