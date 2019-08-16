// @flow
import React from "react"
import { Route, Switch } from "react-router-dom"

import { routes } from "../../../lib/urls"

import B2BPurchasePage from "./B2BPurchasePage"
import B2BReceiptPage from "./B2BReceiptPage"

const EcommerceBulkPages = () => (
  <React.Fragment>
    <Switch>
      <Route
        exact
        path={routes.ecommerceBulk.bulkPurchase}
        component={B2BPurchasePage}
      />
      <Route
        exact
        path={routes.ecommerceBulk.receipt}
        component={B2BReceiptPage}
      />
    </Switch>
  </React.Fragment>
)

export default EcommerceBulkPages
