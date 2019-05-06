/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/

$(document).ready(function() {
  $(".nav-item").click(function() {
    // Remove the class 'active' from other anchors and applied to the current selected.

    $(".nav-item")
      .find("a:first")
      .removeClass("active");
    $(this)
      .find("a:first")
      .addClass("active");
  });
});
