/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/

export default function testimonialsCarousel() {
  const numTestimonialSlides = $(".learners-slider .slide").length;

  $(".learners-slider").slick({
    rows:           0,
    slidesToShow:   3,
    slidesToScroll: 1,
    dots:           numTestimonialSlides > 3,
    infinite:       false,
    autoplay:       false,
    responsive:     [
      {
        breakpoint: 1024,
        settings:   {
          slidesToShow:   3,
          slidesToScroll: 3,
          dots:           numTestimonialSlides > 3
        }
      },
      {
        breakpoint: 992,
        settings:   {
          slidesToShow:   2,
          slidesToScroll: 1,
          dots:           numTestimonialSlides > 2
        }
      },
      {
        breakpoint: 767,
        settings:   {
          slidesToShow:   1,
          slidesToScroll: 1,
          dots:           numTestimonialSlides > 1
        }
      }
    ]
  });
}
