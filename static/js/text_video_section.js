/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/
/* global Hls */

function initializeHlsVideo(VideoSelector) {
  const video = VideoSelector.get(0);

  if (video) {
    const videoUrl = VideoSelector.data("source");
    if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(videoUrl);
      hls.attachMedia(video);
    } // eslint-disable-line brace-style
    // hls.js is not supported on platforms that do not have Media Source Extensions (MSE) enabled.
    // When the browser has built-in HLS support (check using `canPlayType`), we can provide an HLS manifest (i.e. .m3u8 URL) directly to the video element throught the `src` property.
    // This is using the built-in support of the plain video element, without using hls.js.
    // Note: it would be more normal to wait on the 'canplay' event below however on Safari (where you are most likely to find built-in HLS support) the video.src URL must be on the user-driven
    // white-list before a 'canplay' event will be emitted; the last video event that can be reliably listened-for when the URL is not on the white-list is 'loadedmetadata'.
    else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = videoUrl;
    }
  }
}

export default function textVideoSection() {
  const tvVideo = $("#tv-video");
  const lightBoxVideo = $("#tv-light-box-video");
  initializeHlsVideo(tvVideo);
  initializeHlsVideo(lightBoxVideo);
}
