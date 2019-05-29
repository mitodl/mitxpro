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

$(".logos-slider").slick({
  slidesToShow:   6,
  slidesToScroll: 3,
  dots:           true,
  infinite:       true,
  autoplay:       true,
  autoplaySpeed:  2000,
  responsive:     [
    {
      breakpoint: 1200,
      settings:   {
        slidesToShow: 4
      }
    },
    {
      breakpoint: 992,
      settings:   {
        slidesToShow: 3
      }
    },
    {
      breakpoint: 767,
      settings:   {
        slidesToShow: 2
      }
    }
  ]
});
