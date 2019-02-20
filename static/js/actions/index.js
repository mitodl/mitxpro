// @flow
export const UPDATE_CHECKBOX = "UPDATE_CHECKBOX"

export const updateCheckbox = (checked: boolean) => ({
  type:    UPDATE_CHECKBOX,
  payload: { checked }
})
