/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/

export default function productDetails() {
  const navbar = $("#subNavBarContainer");

  // Makes sure to run the script only when DOM conatins #subNavBarContainer (i.e on product page)
  if (navbar.length) {
    // FAQs
    $("body").on("click", ".readmore", function(e) {
      const $readmoreText = $(this).find(".readmore-text");
      e.preventDefault();
      $("li.extra-faq").toggleClass("d-none");
      $readmoreText.text($readmoreText.text() === "Hide" ? "Read" : "Hide");
    });

    // More Dates
    $(".dates-tooltip").popover({
      template:
        '<div class="popover" role="tooltip">' +
        '<div class="arrow"></div>' +
        '<div class="popover-header py-2 px-0 mx-5"></div>' +
        '<div class="popover-body"></div>' +
        "</div>"
    });

    // Navigation Bar
    $("body").scrollspy({
      target: "#subNavBar",
      offset: navbar.outerHeight() + 5.0
    });

    $(window).on("activate.bs.scrollspy", function(e, obj) {
      $("#subNavBarSelector").text(
        $(`.navbar-nav>li>a[href='${obj.relatedTarget}']`).text()
      );
    });

    $(".navbar-nav>li>a").on("click", function(event) {
      event.preventDefault();

      const target = $($(this).attr("href"));

      window.scrollTo(0, target.offset().top - navbar.outerHeight());

      $(".navbar-collapse.show").removeClass("show");
      $(".navbar-toggler").addClass("collapsed");
    });
  }
}
