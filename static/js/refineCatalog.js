/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/
/* eslint-disable no-unused-vars */

export default function refineCatalogCourses(filterClass, filterParamName) {
  $(`.${filterClass}`).on("click", function (event) {
    event.preventDefault();
    const tabName =
      document.querySelector(".nav-link.active").parentElement.dataset.tabName;
    const url = new URL(window.location.href);
    const searchParams = url.searchParams;
    searchParams.set(filterParamName, $(event.target).attr("data-value"));
    searchParams.set("active-tab", tabName);
    url.search = searchParams.toString();
    window.location.href = url.toString();
  });
}
