// @flow
export type CourseRun = {
  title: string,
  start_date: string|null,
  end_date: string|null,
  enrollment_start: string|null,
  enrollment_end: string|null,
  courseware_url_path: string | null,
  courseware_id: string,
  id: number,
}

export type Course = {
  id: number,
  title: string,
  description: string|null,
  thumbnail_url: string,
  readable_id: string|null,
  courseruns: Array<CourseRun>
}
