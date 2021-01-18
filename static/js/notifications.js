/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/

function renderSiteNotification() {
  const notificationId = $(".notification").data("notification-id");

  if (notificationId) {
    if (
      localStorage.getItem("dismissedNotification") !==
      notificationId.toString()
    ) {
      $(".notifications").removeClass("d-none");
    }
  }
}

export default function notifications() {
  renderSiteNotification();

  $(".notifications").on("click", ".close-notification", function(e) {
    e.preventDefault();
    const $notification = $(this).closest(".notification");
    localStorage.setItem(
      "dismissedNotification",
      $notification.data("notification-id")
    );
    $notification.remove();
  });
}
