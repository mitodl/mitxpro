// @flow
import casual from "casual-browserify"

import type { CourseRun } from "../flow/courseTypes"

export const makeCourseRun = (): CourseRun => ({
  title:               casual.text,
  courseware_id:       casual.word,
  courseware_url_path: casual.url,
  start_date:          null,
  end_date:            null,
  enrollment_start:    null,
  enrollment_end:      null,
  live:                casual.boolean
})
