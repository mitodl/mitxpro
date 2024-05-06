// @flow
import React from "react";
import { Redirect, Route, Switch, Link } from "react-router-dom";

import { routes } from "../../../lib/urls";

import CouponCreationPage from "./CreateCouponPage";

const EcommerceAdminIndexPage = () => (
  <div className="ecommerce-admin-body">
    <h3>Ecommerce Admin</h3>
    <ul>
      <li>
        <Link to={routes.ecommerceAdmin.coupons}>Create a Coupon</Link>
      </li>
    </ul>
  </div>
);

const EcommerceAdminPages = () => (
  <React.Fragment>
    <Switch>
      <Route
        exact
        path={routes.ecommerceAdmin.index}
        component={EcommerceAdminIndexPage}
      />
      <Route
        exact
        path={routes.ecommerceAdmin.coupons}
        component={CouponCreationPage}
      />
      <Redirect to={routes.ecommerceAdmin.index} />
    </Switch>
  </React.Fragment>
);

export default EcommerceAdminPages;
