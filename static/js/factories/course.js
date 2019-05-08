// @flow
import { range } from "ramda"
import casual from "casual-browserify"

import type { Course, CourseRun } from "../flow/courseTypes"

export const makeCourseRun = (): CourseRun => ({
  title:               casual.text,
  start_date:          casual.moment.add(2, "M").format(),
  end_date:            casual.moment.add(4, "M").format(),
  enrollment_start:    casual.moment.add(-1, "M").format(),
  enrollment_end:      casual.moment.add(3, "M").format(),
  courseware_url_path: casual.url,
  courseware_id:       casual.word,
  id:                  casual.integer(0, 100)
})

export const makeCourse = (): Course => ({
  id:            casual.integer(0, 100),
  title:         casual.text,
  description:   casual.text,
  thumbnail_url: casual.url,
  readable_id:   casual.text,
  courseruns:    range(0, 3).map(() => makeCourseRun())
})
