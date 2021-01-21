/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/

const numLogoSlides = $(".logos-slider .slide").length;

export default function imageCarousel() {
  $(".logos-slider").slick({
    rows:           0,
    slidesToShow:   6,
    slidesToScroll: 3,
    infinite:       false,
    autoplay:       false,
    dots:           numLogoSlides > 6,
    autoplaySpeed:  2000,
    responsive:     [
      {
        breakpoint: 1200,
        settings:   {
          slidesToShow: 4,
          dots:         numLogoSlides > 4
        }
      },
      {
        breakpoint: 992,
        settings:   {
          slidesToShow: 3,
          dots:         numLogoSlides > 3
        }
      },
      {
        breakpoint: 767,
        settings:   {
          slidesToShow:   2,
          slidesToScroll: 2,
          dots:           numLogoSlides > 2
        }
      }
    ]
  });
}
