/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/
/* eslint-disable no-unused-vars */
export default function applyTopicFilter() {
  $(".topic-filter-option").on("click", function (event) {
    event.preventDefault();
    const url = new URL(window.location.href);
    const searchParams = url.searchParams;
    searchParams.set("topic", $(event.target).attr("data-filter-value"));
    url.search = searchParams.toString();
    window.location.href = url.toString();
  });
}
