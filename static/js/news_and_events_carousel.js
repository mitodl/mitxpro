/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/

export default function newsAndEventsCarousel() {
  const numSlides = $(".news-and-events-slider .slide").length;

  $(".news-and-events-slider").slick({
    rows:           0,
    slidesToShow:   3,
    slidesToScroll: 1,
    dots:           numSlides > 3,
    infinite:       false,
    autoplay:       false,
    responsive:     [
      {
        breakpoint: 1024,
        settings:   {
          slidesToShow:   3,
          slidesToScroll: 3,
          dots:           numSlides > 3
        }
      },
      {
        breakpoint: 992,
        settings:   {
          slidesToShow:   2,
          slidesToScroll: 1,
          dots:           numSlides > 2
        }
      },
      {
        breakpoint: 767,
        settings:   {
          slidesToShow:   1,
          slidesToScroll: 1,
          dots:           numSlides > 1
        }
      }
    ]
  });
}
