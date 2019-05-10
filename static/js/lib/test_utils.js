// @flow
import { assert } from "chai"

import { S } from "./sanctuary"
import { shallow } from "enzyme/build"
import React from "react"

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

/**
 * This is here to support testing components that are wrapped with a
 * context consumer, e.g.:
 *   <SomeContext.Consumer>
 *     {(context) => (<MyComponent myProp={context} />)}
 *   </SomeContext.Consumer>
 *
 * @param WrappedComponent - The wrapped component (e.g.: <SomeContext.Consumer> in the example above)
 * @param props - Props to pass into the wrapped component.
 * @param context - The value to set the context to.
 * @return {Object} - Object with 2 properties. "inner": the inner component with the context
 *   set as desired, "outer": the wrapped component
 */
export const getComponentWithContext = (
  WrappedComponent: Class<React.Component<*, *>>,
  props: Object,
  context: string | Object
) => {
  const outer = shallow(<WrappedComponent {...props} />)
  const inner = outer.props().children(context)
  return { inner, outer }
}

export const shouldIf = (tf: boolean) => (tf ? "should" : "should not")

export const shouldIfGt0 = (num: number) => shouldIf(num > 0)

export const isIf = (tf: boolean) => (tf ? "is" : "is not")
