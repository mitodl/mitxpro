// @flow
export type CourseRun = {
  title: string,
  start_date: ?string,
  end_date: ?string,
  enrollment_start: ?string,
  enrollment_end: ?string,
  courseware_url: ?string,
  courseware_id: string,
  id: number,
  product_id: ?number
}

export type BaseCourse = {
  id: number,
  title: string,
  description: ?string,
  thumbnail_url: string,
  readable_id: ?string
}

export type Course = BaseCourse & {
  courseruns: Array<CourseRun>
}

export type CourseRunDetail = CourseRun & {
  course: BaseCourse
}

export type Program = {
  id: number,
  title: string,
  description: string,
  thumbnail_url: string,
  readable_id: string
}

export type CourseRunEnrollment = {
  run: CourseRunDetail
}

export type ProgramEnrollment = {
  id: number,
  program: Program,
  course_run_enrollments: Array<CourseRunEnrollment>
}

export type UserEnrollments = {
  program_enrollments: Array<ProgramEnrollment>,
  course_run_enrollments: Array<CourseRunEnrollment>
}
