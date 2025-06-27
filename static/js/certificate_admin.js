document.addEventListener("DOMContentLoaded", function () {
  const partnerLogoInput = document.querySelector('[name="partner_logo"]');
  const displayMitSealField = document
    .querySelector('[name="display_mit_seal"]')
    .closest(".w-panel");

  function toggleSealField() {
    if (partnerLogoInput && partnerLogoInput.value) {
      displayMitSealField.style.display = "block";
    } else {
      displayMitSealField.style.display = "none";
    }
  }

  toggleSealField();

  const observer = new MutationObserver(toggleSealField);
  observer.observe(partnerLogoInput, {
    attributes: true,
    childList: true,
    subtree: true,
  });
});
