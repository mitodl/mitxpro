/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/
/* global Hls */
/* eslint-disable no-unused-vars */

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

  // The action button is supposed to play a video element in light box.
  // which exists in another section, which is why we need to check for
  // its existence before we try anything.
  $("#actionButton").on("click", function(event) {
    event.preventDefault();

    const hlsAboutVideo = $("#tv-light-box-video").get(0);
    const aboutVideoYoutube = $("#tv-yt-light-box-video")
      .find("iframe")
      .get(0);

    if (hlsAboutVideo) {
      showLightBox();
      hlsAboutVideo.play();
    } else if (aboutVideoYoutube) {
      showLightBox();
      aboutVideoYoutube.contentWindow.postMessage(
        JSON.stringify({
          event: "command",
          func:  "playVideo"
        }),
        "https://www.youtube.com"
      );
    } else {
      console.error("We do not have any supported video elements available."); // eslint-disable-line no-console
    }
  });
});

function closeLightBox() {
  // Closes the light box.

  const hlsAboutVideo = $("#tv-light-box-video").get(0);
  const aboutVideoYoutube = $("#tv-yt-light-box-video")
    .find("iframe")
    .get(0);

  if (hlsAboutVideo) {
    hlsAboutVideo.pause();
  }

  if (aboutVideoYoutube) {
    aboutVideoYoutube.contentWindow.postMessage(
      JSON.stringify({
        event: "command",
        func:  "stopVideo"
      }),
      "https://www.youtube.com"
    );
  }
  $("body").removeClass("light-box");
  $(".light-box-video-container #light-box")[0].style.display = "none";
  $(".light-box-video-container #fade-light-box")[0].style.display = "none";
}

function showLightBox() {
  // Show up the light box.
  $("body").addClass("light-box");
  $(".light-box-video-container #light-box")[0].style.display = "block";
  $(".light-box-video-container #fade-light-box")[0].style.display = "block";
}
