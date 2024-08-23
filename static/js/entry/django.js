// Third-party imports
import "jquery";
import "bootstrap";
import "popper.js";
import "@popperjs/core";
import "slick-carousel";
import "hls.js";
import "@fancyapps/fancybox";

// Custom native imports
import notifications from "../notifications.js";
import tooltip from "../tooltip.js";
import hero from "../hero.js";
import testimonialsCarousel from "../testimonials_carousel.js";
import newsAndEventsCarousel from "../news_and_events_carousel.js";
import coursewareCarousel from "../courseware_carousel.js";
import textVideoSection from "../text_video_section.js";
import imageCarousel from "../image_carousel.js";
import facultyCarousel from "../faculty_carousel.js";
import productDetails from "../product_detail.js";
import topicsCarousel from "../catalog-topics-carousel.js";
import blogPostsCarousel from "../blog_posts_carousel";
import companiesLogoCarousel from "../companies_logo_carousel.js";
import successStoriesCarousel from "../success_stories_carousel.js";

document.addEventListener("DOMContentLoaded", function () {
  notifications();
  tooltip();
  hero();
  testimonialsCarousel();
  newsAndEventsCarousel();
  coursewareCarousel();
  topicsCarousel();
  blogPostsCarousel();
  textVideoSection();
  imageCarousel();
  facultyCarousel();
  productDetails();
  companiesLogoCarousel();
  successStoriesCarousel();
});
