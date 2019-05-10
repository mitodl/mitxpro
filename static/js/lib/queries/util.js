// @flow
import { nthArg } from "ramda"

// replace the previous state with the next state without merging
export const nextState = nthArg(1)
