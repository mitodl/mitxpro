import {objOf, pathOr} from "ramda"
import type {CourseTopic} from "../../flow/courseTypes"
import {nextState} from "./util"

export default {
  courseTopicsSelector: pathOr(null, ["entities", "courseTopics"]),
  courseTopicsQuery:    () => ({
    queryKey:  "parent_course_topics",
    url:       "/api/parent_course_topics/",
    transform: (json: Array<CourseTopic>) => ({
      courseTopics: json
    }),
    update: {
      courseTopics: nextState
    }
  }),
}
