document.addEventListener("DOMContentLoaded", function () {
  const accordionButtons = document.querySelectorAll(".chapter-button");

  accordionButtons.forEach((button) => {
    button.addEventListener("click", function () {
      setTimeout(() => {
        const target = document.querySelector(this.dataset.bsTarget);

        if (target && !this.classList.contains("collapsed")) {
          target.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
          });
        }
      }, 300);
    });
  });
});
