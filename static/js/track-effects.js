function observeTracks() {
  const tracks = [...document.querySelectorAll(".track-map")];
  if (!("IntersectionObserver" in window)) {
    tracks.forEach((track) => track.classList.add("is-visible"));
    return;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.22 },
  );
  tracks.forEach((track) => observer.observe(track));
}

function tiltCards() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  for (const element of document.querySelectorAll("[data-event-card], [data-track-tilt]")) {
    element.addEventListener("pointermove", (event) => {
      const bounds = element.getBoundingClientRect();
      const x = (event.clientX - bounds.left) / bounds.width - 0.5;
      const y = (event.clientY - bounds.top) / bounds.height - 0.5;
      element.style.setProperty("--tilt-x", `${-y * 4}deg`);
      element.style.setProperty("--tilt-y", `${x * 5}deg`);
    });
    element.addEventListener("pointerleave", () => {
      element.style.setProperty("--tilt-x", "0deg");
      element.style.setProperty("--tilt-y", "0deg");
    });
  }
}

export function initTrackEffects() {
  observeTracks();
  tiltCards();
}
