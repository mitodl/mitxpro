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
const genProductId = incrementer()
const genCoursewareId = incrementer()
const genRunTagNumber = incrementer()
const genReadableId = incrementer()

export const makeCourseRun = (): CourseRun => ({
  title:            casual.text,
  start_date:       casual.moment.add(2, "M").format(),
  end_date:         casual.moment.add(4, "M").format(),
  enrollment_start: casual.moment.add(-1, "M").format(),
  enrollment_end:   casual.moment.add(3, "M").format(),
  courseware_url:   casual.url,
  courseware_id:    casual.word.concat(genCoursewareId.next().value),
  run_tag:          casual.word.concat(genRunTagNumber.next().value),
  // $FlowFixMe
  id:               genCourseRunId.next().value,
  product_id:       genProductId.next().value
})

const genCourseId = incrementer()
const makeBaseCourse = (nextRunId: ?number): BaseCourse => ({
  // $FlowFixMe
  id:            genCourseId.next().value,
  title:         casual.text,
  description:   casual.text,
  thumbnail_url: casual.url,
  readable_id:   casual.word,
  next_run_id:   nextRunId
})

export const makeCourse = (): Course => {
  const runs = range(0, 3).map(() => makeCourseRun())
  const baseCourse = makeBaseCourse(runs[1].id)

  return {
    ...baseCourse,
    courseruns: runs
  }
}

const genProgramId = incrementer()
export const makeProgram = (): Program => ({
  // $FlowFixMe
  id:            genProgramId.next().value,
  title:         casual.text,
  description:   casual.text,
  thumbnail_url: casual.url,
  readable_id:   casual.word.concat(genReadableId.next().value)
})

export const makeCourseRunDetail = (): CourseRunDetail => {
  const run = makeCourseRun()
  return {
    ...makeCourseRun(),
    course: makeBaseCourse(run.id)
  }
}

export const makeCourseRunEnrollment = (): CourseRunEnrollment => ({
  run:         makeCourseRunDetail(),
  certificate: null,
  receipt:     null
})

const genProgramEnrollmentId = incrementer()
export const makeProgramEnrollment = (): ProgramEnrollment => ({
  // $FlowFixMe
  id:                     genProgramEnrollmentId.next().value,
  program:                makeProgram(),
  course_run_enrollments: [
    makeCourseRunEnrollment(),
    makeCourseRunEnrollment()
  ],
  certificate: null,
  receipt:     null
})

export const makeUserEnrollments = (): UserEnrollments => ({
  program_enrollments:    [makeProgramEnrollment()],
  course_run_enrollments: [
    makeCourseRunEnrollment(),
    makeCourseRunEnrollment()
  ],
  past_program_enrollments:    [makeProgramEnrollment()],
  past_course_run_enrollments: [
    makeCourseRunEnrollment(),
    makeCourseRunEnrollment()
  ]
})
