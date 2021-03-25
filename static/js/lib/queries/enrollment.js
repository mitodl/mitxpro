import { pathOr } from "ramda"

import { nextState } from "./util"
import { getCookie } from "../api"

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
  }),

  courseDigitalCredentialDownload: (uuid: string) => ({
    queryKey: "digitalCredentialDownload",
    url:      `/api/v1/course_run_certificates/${uuid}/request-digital-credential`,
    body:     {},
    options:  {
      method:  "POST",
      headers: {
        "X-CSRFTOKEN": getCookie("csrftoken")
      }
    }
  })
}
