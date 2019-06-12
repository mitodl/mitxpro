/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/
$(".learners-slider").slick({
  slidesToShow:   3,
  slidesToScroll: 1,
  dots:           true,
  infinite:       false,
  autoplay:       false,
  responsive:     [
    {
      breakpoint: 1024,
      settings:   {
        slidesToShow:   3,
        slidesToScroll: 3,
        infinite:       false,
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
