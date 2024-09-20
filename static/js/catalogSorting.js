/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/
/* eslint-disable no-unused-vars */
export default function applySorting() {
  $(".catalog-sort-option").on("click", function (event) {
    event.preventDefault();
    const url = new URL(window.location.href);
    const searchParams = url.searchParams;
    searchParams.set("sort-by", $(event.target).attr("data-sort-value"));
    url.search = searchParams.toString();
    window.location.href = url.toString();
  });
}
