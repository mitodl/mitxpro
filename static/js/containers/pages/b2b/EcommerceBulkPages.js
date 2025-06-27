// @flow
import React from "react";
import { Routes, Route } from "react-router-dom";

import { routes } from "../../../lib/urls";

import B2BPurchasePage from "./B2BPurchasePage";
import B2BReceiptPage from "./B2BReceiptPage";

const EcommerceBulkPages = () => (
  <React.Fragment>
    <Routes>
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
    </Routes>
  </React.Fragment>
);

export default EcommerceBulkPages;
