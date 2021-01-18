/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/
/* global Hls */
/* eslint-disable no-unused-vars */
const backgroundVideoSel = "#background-video";
const promoVideoSel = "#promo-video";

function openVideoLightBox() {
  const youtubeVideoSrc = $("#tv-light-box-yt-video").attr("data-href");
  const hlsAboutVideoEl = $("video#tv-light-box-video");
  if (!youtubeVideoSrc && hlsAboutVideoEl.length === 0) {
    console.error("We do not have any supported video elements available."); // eslint-disable-line no-console
    return;
  }

  let backgroundVideo = null;
  const fancyBoxArgs = $.extend(
    {},
    {
      beforeShow: function() {
        backgroundVideo = $(backgroundVideoSel).get(0);
      },
      beforeLoad: function() {
        backgroundVideo && backgroundVideo.pause();
      },
      afterClose: function() {
        backgroundVideo && backgroundVideo.play();
      }
    },
    youtubeVideoSrc
      ? {
        src: youtubeVideoSrc
      }
      : {
        content: hlsAboutVideoEl,
        type:    "html"
      }
  );
  $.fancybox.open(fancyBoxArgs);
}

function configureHlsVideo(selector, autoplay) {
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
    } // eslint-disable-line brace-style
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

export default function hero() {
  // Background cover video in header on home page
  configureHlsVideo(backgroundVideoSel, true);

  // Promo video in header on product detail page
  configureHlsVideo(promoVideoSel);

  // The action button is supposed to play a video element in light box.
  // which exists in another section, which is why we need to check for
  // its existence before we try anything.
  $("#actionButton").on("click", function(event) {
    event.preventDefault();
    openVideoLightBox();
  });
}
