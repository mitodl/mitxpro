/*eslint-env jquery*/
/*eslint semi: ["error", "always"]*/

export default function wagtailLazyLoader() {
  const observerConfig = {
    root:       null,
    rootMargin: "0px",
    threshold:  0
  };

  const imgs = document.querySelectorAll(".wagtail-lazy-load");

  const observer = new IntersectionObserver(function(entries, observer) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        entry.target.src = entry.target.dataset.src;
        observer.unobserve(entry.target);
      }
    });
  }, observerConfig);

  imgs.forEach(image => {
    observer.observe(image);
  });
}
