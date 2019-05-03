/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/

$(document).ready(function() {
  $("body").on("click", ".readmore", function(e) {
    const $readmoreText = $(this).find(".readmore-text");
    e.preventDefault();
    $("li.extra-faq").toggleClass("d-none");
    $readmoreText.text($readmoreText.text() === "Hide" ? "Read" : "Hide");
  });
});
