/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/
/* eslint-disable no-unused-vars */
export default function applyLanguageFilter() {
  $(".language-filter-option").on("click", function (event) {
    event.preventDefault();
    const url = new URL(window.location.href);
    const searchParams = url.searchParams;
    searchParams.set("language", $(event.target).attr("data-filter-value"));
    url.search = searchParams.toString();
    window.location.href = url.toString();
  });
}
