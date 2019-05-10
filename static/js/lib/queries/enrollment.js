import { pathOr } from "ramda"

import { nextState } from "./util"

export default {
  enrollmentsSelector: pathOr(null, ["entities", "enrollments"]),
  enrollmentsQuery:    () => ({
    url:       "/api/enrollments/",
    transform: json => ({
      enrollments: json
    }),
    update: {
      enrollments: nextState
    }
  })
}
