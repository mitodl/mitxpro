// @flow
export type BaseCourseRun = {
  title: string,
  start_date: ?string,
  end_date: ?string,
  enrollment_start: ?string,
  enrollment_end: ?string,
  courseware_url: ?string,
  courseware_id: string,
  run_tag: ?string,
  id: number
}

export type CourseRun = BaseCourseRun & {
  product_id: ?number
}

export type BaseCourse = {
  id: number,
  title: string,
  description: ?string,
  thumbnail_url: string,
  readable_id: ?string,
  next_run_id: ?number
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

export type CourseRunCertificate = {
  link: string,
  uuid: string
}

export type ProgramCertificate = {
  link: string,
  uuid: string
}

export type CourseRunEnrollment = {
  run: CourseRunDetail,
  certificate: ?CourseRunCertificate,
  receipt: ?number
}

export type ProgramEnrollment = {
  id: number,
  program: Program,
  course_run_enrollments: Array<CourseRunEnrollment>,
  certificate: ?ProgramCertificate,
  receipt: ?number
}

export type UserEnrollments = {
  program_enrollments: Array<ProgramEnrollment>,
  course_run_enrollments: Array<CourseRunEnrollment>,
  past_program_enrollments: Array<ProgramEnrollment>,
  past_course_run_enrollments: Array<CourseRunEnrollment>
}
