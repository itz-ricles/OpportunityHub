// Mobile navigation toggle
const toggle = document.querySelector(".nav-toggle");
const menu = document.getElementById("nav-menu");
if (toggle && menu) {
  toggle.addEventListener("click", () => {
    const open = menu.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
  });
}

// Ask before destructive actions: <form data-confirm="Are you sure?">
document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});
