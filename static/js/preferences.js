function csrfToken(form) {
  return form.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
}

async function postForm(form, formData = new FormData(form)) {
  const response = await fetch(form.action, {
    method: "POST",
    body: formData,
    credentials: "same-origin",
    headers: { "X-CSRFToken": csrfToken(form), "X-Requested-With": "fetch" },
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

function formatTimes(timezone) {
  let fullFormatter;
  let compactFormatter;
  try {
    fullFormatter = new Intl.DateTimeFormat("ru-RU", {
      timeZone: timezone,
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
    compactFormatter = new Intl.DateTimeFormat("ru-RU", {
      timeZone: timezone,
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch (_) {
    return;
  }
  const timezoneLabel = timezone === "Europe/Moscow" ? "МСК" : timezone;
  for (const time of document.querySelectorAll("time[data-utc]")) {
    const date = new Date(time.dataset.utc);
    if (!Number.isNaN(date.getTime())) {
      if (time.dataset.timeFormat === "compact") {
        time.textContent = `${compactFormatter.format(date)} ${timezoneLabel}`;
      } else {
        time.textContent = `${fullFormatter.format(date).replace(",", " ·")} · ${timezoneLabel}`;
      }
    }
  }
}

function addBrowserTimezone(select) {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  if (!timezone || [...select.options].some((option) => option.value === timezone)) return;
  const option = new Option(`Устройство · ${timezone}`, timezone);
  select.add(option);
  if (document.body.dataset.timezone === timezone) select.value = timezone;
}

function initTimezonePreferences() {
  const form = document.querySelector("[data-preference-form]");
  const select = form?.querySelector("[data-timezone-select]");
  if (!form || !select) return;
  addBrowserTimezone(select);
  formatTimes(select.value);

  select.addEventListener("change", async () => {
    const formData = new FormData(form);
    select.disabled = true;
    try {
      const data = await postForm(form, formData);
      document.body.dataset.timezone = data.timezone;
      if (document.querySelector("[data-timezone-regroup]")) {
        window.location.reload();
        return;
      }
      formatTimes(data.timezone);
    } catch (_) {
      form.submit();
    } finally {
      select.disabled = false;
    }
  });
}

function initFavoritePreferences() {
  for (const form of document.querySelectorAll("[data-favorite-form]")) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      if (!button) return;
      button.disabled = true;
      try {
        const data = await postForm(form);
        button.setAttribute("aria-pressed", String(data.is_favorite));
        button.innerHTML = data.is_favorite
          ? '<span aria-hidden="true">★</span> Убрать из избранного'
          : '<span aria-hidden="true">★</span> Добавить в избранное';
      } catch (_) {
        form.submit();
      } finally {
        button.disabled = false;
      }
    });
  }
}

export function initPreferences() {
  initTimezonePreferences();
  initFavoritePreferences();
}

export { postForm };
