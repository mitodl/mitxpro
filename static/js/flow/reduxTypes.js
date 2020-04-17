// @flow
export type ActionType = string

export type Action<payload, meta> = {
  type: ActionType,
  payload: payload,
  meta: meta
}
