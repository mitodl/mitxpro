// @flow
import { mutateAsync } from "redux-query"

import { deleteCourseRequest, updateCourseRequest } from "../lib/api"

export const UPDATE_CHECKBOX = "UPDATE_CHECKBOX"

export const updateCheckbox = (checked: boolean) => ({
  type:    UPDATE_CHECKBOX,
  payload: { checked }
})

export const deleteCourse = (courseId: number) => {
  return mutateAsync(deleteCourseRequest(courseId))
}

export const updateCourse = (courseId: number, payload: Object) => {
  return mutateAsync(updateCourseRequest(courseId, payload))
}
