## Making mitxpro bot-friendly

## Abstract

In Open Discussions we ran into an issue that is common for single page 
apps in general. We wanted to add some `<meta>` tags to certain pages that
would create an attractive preview when shared on Facebook (for an example, 
look at the Link Preview section [here](https://developers.facebook.com/tools/debug/sharing/?q=http%3A%2F%2Fmit.edu)).
The problem: Facebook has a crawler that scans for these particular `<meta>`
tags to create that preview, but it doesn't execute any Javascript. As a result,
the crawler could only see the basically-empty Django template for the page.

In Open Discussions we ended up serving up a basic page with no content and
some default `<meta>` tags for all requests from the Facebook crawler user agent. 
In xpro, we will almost definitely want to support Facebook link previews, and
we will want to have different previews for different pages (e.g.: on a course
detail page, show the actual course image and course title rather than some default 
image/text).

Based on prior app usage (and complaints), we are also anticipating that we'll 
have some users that prefer not to run Javascript.

This RFC aims to lay out our options for addressing those issues, list some advantages and
drawbacks, and gather feedback about which option to take.

## Options

#### 1) Serve specific content to the Facebook user agent (like we do in OD)

With this approach, we would have some specialized logic for rendering a Django
template if the request has the Facebook crawler user agent. Depending on the 
route being requested, we would provide different bits of template data. For example,
if the request was for the root URL, we would render the template with some default title
value. If the request was for a specific course detail page, we would render the template
with the course title as the title value.

*Advantages:*
1. Easiest and quickest option. Easy to implement alongside our current patterns and UI 'philosophy'.
1. No new libraries/tools to learn.

*Drawbacks:*
1. Logic copying and the possibility of drift. With this approach we would have
  two different sets of logic for rendering some routes, and it would be split
  between the front- and back-end. It would also be possible for the front- and 
  back-end logic to drift, i.e.: the front-end renders some content for a route that
  doesn't match the Facebook link preview content for the same route.
1. If any new pages/routes were created for which we would want some new
  Facebook preview content, it would be very easy to forget to implement the 
  specialized logic for the Facebook-UA-specific template. We'd be much
  more likely to remember if the `<meta>` tag rendering was with the rest of
  the React code (which would be the case if we used server-side rendering).
1. It's possible that we'd want to add support for other bots (Twitter? Google?) in
  the future. That would add some complexity to the template-rendering logic.

#### 2) Server-side rendering

We've discussed the possibility of supporting server-side rendering several times
in the past. Server-side rendering would solve this problem completely because
certain parts of the single page app, namely the `<meta>` tags we care about, could 
be rendered in the browser before JS took over.

*Advantages:*
1. All front-end code would be in React
1. We would get [all of the other bonuses of server-side rendering](https://medium.com/walmartlabs/the-benefits-of-server-side-rendering-over-client-side-rendering-5d07ff2cefe8)
  (better performance, most notably)

*Drawbacks:*
1. Implementation time & difficulty – This would involve tools/libraries that are
  widely used in the greater tech community, but they would be new to most of us.
  I can't predict how long this would take to implement, how much time it would take
  for us to be comfortable with the tooling, and how difficult it would be to maintain.

#### 3) Hybrid approach - some content in Django templates, some content in React

With this approach, we would render some pages mostly or entirely with Django templates
and other pages entirely with React as we have done for our other web apps. 
For example, if we had a page like the course catalog where we didn't expect to have
any interactive elements, we could render most/all of the page in a Django template.

*Advantages:*
1. No need to handle user agents differently.
1. The static pages would basically be as performant as they could be, and we wouldn't
  need to worry about any potential JS-related SEO issues.
1. No more complaints from users that turn off JS in their browsers.
1. We have at least one developer on the team who has experience writing and maintaining
  an app with this half-and-half approach.

*Drawbacks:*
1. Confusion/Ambiguity – In our other apps, we know where basically all of our HTML and 
  our UI routes live. This approach would split that up. It also creates the possibility
  for confusion around where to put new HTML.
1. Rigidity – If we wanted to take a Django template-rendered page and add interactive elements,
  it could be a painful process. Making decisions about what is handled in React and what
  goes in each static asset bundle may be difficult, and we may have trouble implementing
  some UX that would otherwise be very simple with a just-React approach.

#### Author's recommendation: Option 3, with Option 1 mixed in as needed

After talking with Peter and Ferdi, we established a few things:

1. Marketing has specific requirements about SEO. It's not enough to say that Google will
  run JS to make our pages SEO friendly and we'll hack something together wherever we need 
  Facebook preview pages.
1. There are going to be pages with little to no interactive elements (the course
  catalog page chief among them).
1. We intend to support non-JS users, at least for the public-facing pages.

All of this points to to the hybrid approach. If we end up having highly-interactive
JS-only pages for which we want to have some specialized content in the Facebook preview,
we can implement that with option 1. 
