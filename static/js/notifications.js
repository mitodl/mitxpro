/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/

$(document).ready(function() {
  $(".site-wide-notifications").on("click", ".close-alert", function(e) {
    e.preventDefault();
  this.closest('.alert').remove();
  });
});
