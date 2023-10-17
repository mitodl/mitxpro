import { pathOr } from "ramda"

import { nextState } from "./util"

export default {
  blogsSelector:    pathOr(null, ["entities", "blogs"]),
  blogsQuery:    () => ({
    url:       "/api/blog/list/",
    transform: json => ({
      blogs: json
    }),
    update: {
      blogs: nextState
    }
  })
}
