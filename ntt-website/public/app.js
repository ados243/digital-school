const nav = document.getElementById("nav");
const toggle = document.querySelector("[data-menu-toggle]");
const year = document.getElementById("year");
const form = document.getElementById("contact-form");
const statusEl = document.getElementById("form-status");

if (year) year.textContent = String(new Date().getFullYear());

toggle?.addEventListener("click", () => {
  const open = nav.classList.toggle("open");
  toggle.setAttribute("aria-expanded", String(open));
});

document.querySelectorAll('#menu a').forEach((link) => {
  link.addEventListener("click", () => {
    nav.classList.remove("open");
    toggle?.setAttribute("aria-expanded", "false");
  });
});

form?.addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const nom = String(data.get("nom") || "").trim();
  const etablissement = String(data.get("etablissement") || "").trim();
  const email = String(data.get("email") || "").trim();
  const telephone = String(data.get("telephone") || "").trim();
  const objet = String(data.get("objet") || "").trim();
  const message = String(data.get("message") || "").trim();

  const body = [
    `Nom : ${nom}`,
    `Établissement : ${etablissement || "—"}`,
    `E-mail : ${email}`,
    `Téléphone : ${telephone || "—"}`,
    "",
    message,
  ].join("\n");

  const mailto = `mailto:Adoscongo@gmail.com?subject=${encodeURIComponent(`[NTT] ${objet}`)}&body=${encodeURIComponent(body)}`;
  window.location.href = mailto;
  if (statusEl) {
    statusEl.textContent = "Votre application e-mail s’ouvre avec le message prêt à envoyer.";
  }
  form.reset();
});
