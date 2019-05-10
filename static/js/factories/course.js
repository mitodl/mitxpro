// @flow
import { range } from "ramda"
import casual from "casual-browserify"

import { incrementer } from "./util"

import type {
  CourseRun,
  BaseCourse,
  Course,
  CourseRunDetail,
  CourseRunEnrollment,
  Program,
  ProgramEnrollment,
  UserEnrollments
} from "../flow/courseTypes"

const genCourseRunId = incrementer()
export const makeCourseRun = (): CourseRun => ({
  title:            casual.text,
  start_date:       casual.moment.add(2, "M").format(),
  end_date:         casual.moment.add(4, "M").format(),
  enrollment_start: casual.moment.add(-1, "M").format(),
  enrollment_end:   casual.moment.add(3, "M").format(),
  courseware_url:   casual.url,
  courseware_id:    casual.word,
  // $FlowFixMe
  id:               genCourseRunId.next().value
})

const genCourseId = incrementer()
export const makeBaseCourse = (): BaseCourse => ({
  // $FlowFixMe
  id:            genCourseId.next().value,
  title:         casual.text,
  description:   casual.text,
  thumbnail_url: casual.url,
  readable_id:   casual.word
})

export const makeCourse = (): Course => ({
  ...makeBaseCourse(),
  courseruns: range(0, 3).map(() => makeCourseRun())
})

const genProgramId = incrementer()
export const makeProgram = (): Program => ({
  // $FlowFixMe
  id:            genProgramId.next().value,
  title:         casual.text,
  description:   casual.text,
  thumbnail_url: casual.url,
  readable_id:   casual.word
})

export const makeCourseRunDetail = (): CourseRunDetail => ({
  ...makeCourseRun(),
  course: makeBaseCourse()
})

export const makeCourseRunEnrollment = (): CourseRunEnrollment => ({
  run: makeCourseRunDetail()
})

const genProgramEnrollmentId = incrementer()
export const makeProgramEnrollment = (): ProgramEnrollment => ({
  // $FlowFixMe
  id:                     genProgramEnrollmentId.next().value,
  program:                makeProgram(),
  course_run_enrollments: [makeCourseRunEnrollment(), makeCourseRunEnrollment()]
})

export const makeUserEnrollments = (): UserEnrollments => ({
  program_enrollments:    [makeProgramEnrollment()],
  course_run_enrollments: [makeCourseRunEnrollment(), makeCourseRunEnrollment()]
})
