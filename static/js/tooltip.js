/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/
// This method simply initializes all tooltips on the page if they exist.
export default function tooltip() {
  $('[data-toggle="tooltip"]').tooltip();
}
