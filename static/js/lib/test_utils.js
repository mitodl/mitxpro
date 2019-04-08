// @flow
import { assert } from "chai"

import { S } from "./sanctuary"
const { Maybe } = S

export const assertMaybeEquality = (m1: Maybe, m2: Maybe) => {
  assert(S.equals(m1, m2), `expected ${m1.value} to equal ${m2.value}`)
}

export const assertIsNothing = (m: Maybe) => {
  assert(m.isNothing, `should be nothing, is ${m}`)
}

export const assertIsJust = (m: Maybe, val: any) => {
  assert(m.isJust, `should be Just(${val}), is ${m}`)
  assert.deepEqual(m.value, val)
}

export const findFormikFieldByName = (wrapper: any, name: string) =>
  wrapper
    .find("FormikConnect(FieldInner)")
    .filterWhere(node => node.prop("name") === name)

export const findFormikErrorByName = (wrapper: any, name: string) =>
  wrapper
    .find("FormikConnect(ErrorMessageImpl)")
    .filterWhere(node => node.prop("name") === name)
