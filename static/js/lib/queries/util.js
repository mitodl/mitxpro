// @flow
import { nthArg } from "ramda"

import type { QueryState } from "redux-query"

// replace the previous state with the next state without merging
export const nextState = nthArg(1)

export const hasUnauthorizedResponse = (queryState: ?QueryState) =>
  queryState &&
  queryState.isFinished &&
  (queryState.status === 401 || queryState.status === 403)
