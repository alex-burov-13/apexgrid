import { initCountdowns } from "./countdown.js";
import { initPreferences } from "./preferences.js";
import { initCalendarFilters } from "./calendar.js";
import { initCircuitSearch } from "./circuit-gallery.js";
import { initTrackEffects } from "./track-effects.js";

document.documentElement.classList.add("js");

function boot() {
  initCountdowns();
  initPreferences();
  initCalendarFilters();
  initCircuitSearch();
  initTrackEffects();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
  boot();
}
