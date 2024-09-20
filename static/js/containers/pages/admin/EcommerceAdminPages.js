// @flow
import React from "react";
import { Redirect, Route, Switch, Link } from "react-router-dom";

import { routes } from "../../../lib/urls";

import CouponCreationPage from "./CreateCouponPage";
import DeactivateCouponPage from "./DeactivateCouponPage";

const EcommerceAdminIndexPage = () => (
  <div className="ecommerce-admin-body">
    <h3>Ecommerce Admin</h3>
    <ul>
      <li>
        <Link to={routes.ecommerceAdmin.coupons}>Create a Coupon</Link>
      </li>
      <li>
        <Link to={routes.ecommerceAdmin.deactivate}>Deactivate Coupons</Link>
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
      <Route
        exact
        path={routes.ecommerceAdmin.deactivate}
        component={DeactivateCouponPage}
      />
      <Redirect to={routes.ecommerceAdmin.index} />
    </Switch>
  </React.Fragment>
);

export default EcommerceAdminPages;
