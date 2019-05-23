/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/
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
