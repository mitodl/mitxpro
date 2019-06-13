/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/
/* global Hls */

function configureHlsVideo(selector, autoplay = false) {
  const video = $(selector).get(0);

  if (video) {
    const videoUrl = $(selector).data("source");
    if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(videoUrl);
      hls.attachMedia(video);
      if (autoplay) {
        hls.on(Hls.Events.MANIFEST_PARSED, function() {
          video.play();
        });
      }
    }
    // hls.js is not supported on platforms that do not have Media Source Extensions (MSE) enabled.
    // When the browser has built-in HLS support (check using `canPlayType`), we can provide an HLS manifest (i.e. .m3u8 URL) directly to the video element throught the `src` property.
    // This is using the built-in support of the plain video element, without using hls.js.
    // Note: it would be more normal to wait on the 'canplay' event below however on Safari (where you are most likely to find built-in HLS support) the video.src URL must be on the user-driven
    // white-list before a 'canplay' event will be emitted; the last video event that can be reliably listened-for when the URL is not on the white-list is 'loadedmetadata'.
    else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = videoUrl;
      if (autoplay) {
        video.addEventListener("loadedmetadata", function() {
          video.play();
        });
      }
    }
  }
}

$(document).ready(function() {
  // Background cover video in header on home page
  configureHlsVideo("#background-video", true);

  // Promo video in header on product detail page
  configureHlsVideo("#promo-video");

  // The action button is supposed to scroll to and play a video element
  // which exists in another section, which is why we need to check for
  // its existence before we try anything.
  $("#actionButton").on("click", function(event) {
    event.preventDefault();

    const aboutVideo = $("#tv-video").get(0);

    if (aboutVideo) {
      aboutVideo.scrollIntoView({
        behavior: "smooth",
        block:    "center"
      });
      aboutVideo.play();
    }
  });
});
