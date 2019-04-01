// @flow
export type CourseRun = {
  title: string,
  courseware_id: string,
  courseware_url_path: string,
  start_date: ?string,
  end_date: ?string,
  enrollment_start: ?string,
  enrollment_end: ?string,
  live: boolean,
}
