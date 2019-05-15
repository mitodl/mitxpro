/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/

$(document).ready(function() {
  $("body").on("click", ".readmore", function(e) {
    const $readmoreText = $(this).find(".readmore-text");
    e.preventDefault();
    $("li.extra-faq").toggleClass("d-none");
    $readmoreText.text($readmoreText.text() === "Hide" ? "Read" : "Hide");
  });

  $(".dates-tooltip").popover({
    template:
      '<div class="popover" role="tooltip"> \
        <div class="arrow"></div> \
        <div class="popover-header py-2 px-0 mx-5"></div> \
        <div class="popover-body"></div> \
      </div>'
  });

  $("body").scrollspy({ target: "#subNavBar", offset: 70 });

  $(window).on("activate.bs.scrollspy", function(e, obj) {
    $("#subNavBarSelector").text(
      $(`.navbar-nav>li>a[href='${obj.relatedTarget}']`).text()
    );
  });

  $(".navbar-nav>li>a").on("click", function() {
    $(".navbar-collapse.show").removeClass("show");
    $(".navbar-toggler").addClass("collapsed");
  });
});

$(".course-slider").slick({
  slidesToShow:   3,
  slidesToScroll: 1,
  dots:           false,
  infinite:       true,
  autoplay:       true,
  autoplaySpeed:  2000,
  responsive:     [
    {
      breakpoint: 1024,
      settings:   {
        slidesToShow:   3,
        slidesToScroll: 3
      }
    },
    {
      breakpoint: 992,
      settings:   {
        slidesToShow:   2,
        slidesToScroll: 1
      }
    },
    {
      breakpoint: 767,
      settings:   {
        slidesToShow:   1,
        slidesToScroll: 1
      }
    }
  ]
});

$(".faculty-slider").slick({
  slidesToShow:   3,
  slidesToScroll: 1,
  dots:           true,
  infinite:       true,
  autoplay:       false,
  autoplaySpeed:  2000,
  responsive:     [
    {
      breakpoint: 1024,
      settings:   {
        slidesToShow:   3,
        slidesToScroll: 3,
        infinite:       true,
        dots:           true
      }
    },
    {
      breakpoint: 992,
      settings:   {
        slidesToShow:   2,
        slidesToScroll: 1
      }
    },
    {
      breakpoint: 767,
      settings:   {
        slidesToShow:   1,
        slidesToScroll: 1
      }
    }
  ]
});

$(".learners-slider").slick({
  slidesToShow:   3,
  slidesToScroll: 1,
  dots:           true,
  infinite:       true,
  autoplay:       true,
  autoplaySpeed:  2000,
  responsive:     [
    {
      breakpoint: 1024,
      settings:   {
        slidesToShow:   3,
        slidesToScroll: 3,
        infinite:       true,
        dots:           true
      }
    },
    {
      breakpoint: 992,
      settings:   {
        slidesToShow:   2,
        slidesToScroll: 1
      }
    },
    {
      breakpoint: 767,
      settings:   {
        slidesToShow:   1,
        slidesToScroll: 1
      }
    }
  ]
});
