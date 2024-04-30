/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/

export default function successStoriesCarousel() {
  const numSuccessStoriesSlides = $(".success-stories-slider .slide").length;

  $(".success-stories-slider").slick({
    rows: 0,
    slidesToShow: 1,
    slidesToScroll: 1,
    dots: numSuccessStoriesSlides > 1,
    infinite: false,
    autoplay: false,
    responsive: [
      {
        breakpoint: 1024,
        settings: {
          slidesToShow: 1,
          slidesToScroll: 1,
          dots: numSuccessStoriesSlides > 1,
        },
      },
      {
        breakpoint: 992,
        settings: {
          slidesToShow: 1,
          slidesToScroll: 1,
          dots: numSuccessStoriesSlides > 1,
        },
      },
      {
        breakpoint: 767,
        settings: {
          slidesToShow: 1,
          slidesToScroll: 1,
          dots: numSuccessStoriesSlides > 1,
        },
      },
    ],
  });
}
