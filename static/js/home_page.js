/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/
$(".logos-slider").slick({
  slidesToShow:   6,
  slidesToScroll: 3,
  dots:           true,
  infinite:       false,
  autoplay:       false,
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
