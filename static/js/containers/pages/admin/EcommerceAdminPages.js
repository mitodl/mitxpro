// @flow
declare var USER_PERMISSIONS: {
  has_coupon_create_permission: boolean,
  has_coupon_update_permission: boolean,
  has_coupon_product_assignment_permission: boolean,
};
import React from "react";
import { Navigate, Route, Routes, Link } from "react-router-dom";

import { routes } from "../../../lib/urls";

import CouponCreationPage from "./CreateCouponPage";
import DeactivateCouponPage from "./DeactivateCouponPage";
import ProcessCouponAssignmentSheetPage from "./ProcessCouponAssignmentSheetPage";
import UpdatePromoCodePage from "./UpdatePromoCouponPage";

const EcommerceAdminIndexPage = () => (
  <div className="ecommerce-admin-body">
    <h3>Ecommerce Admin</h3>
    <ul>
      {USER_PERMISSIONS.has_coupon_create_permission && (
        <li>
          <Link to={routes.ecommerceAdmin.coupons}>Create a Coupon</Link>
        </li>
      )}
      {USER_PERMISSIONS.has_coupon_update_permission && (
        <li>
          <Link to={routes.ecommerceAdmin.deactivate}>
            Deactivate Coupon(s)
          </Link>
        </li>
      )}
      {USER_PERMISSIONS.has_coupon_product_assignment_permission && (
        <li>
          <Link to={routes.ecommerceAdmin.processSheets}>
            Process Coupon Assignment Sheet
          </Link>
        </li>
      )}
      {USER_PERMISSIONS.has_coupon_update_permission && (
        <li>
          <Link to={routes.ecommerceAdmin.updatePromoCode}>
            Update Promo Coupon
          </Link>
        </li>
      )}
    </ul>
  </div>
);

const EcommerceAdminPages = () => (
  <React.Fragment>
    <Routes>
      <Route
        exact
        path={routes.ecommerceAdmin.index}
        element={<EcommerceAdminIndexPage />}
      />
      <Route
        exact
        path={routes.ecommerceAdmin.coupons.create}
        element={<CouponCreationPage />}
      />
      <Route
        exact
        path={routes.ecommerceAdmin.coupons.deactivate}
        element={<DeactivateCouponPage />}
      />
      <Route
        exact
        path={routes.ecommerceAdmin.coupons.processAssignmentSheet}
        element={<ProcessCouponAssignmentSheetPage />}
      />
      <Route
        exact
        path={routes.ecommerceAdmin.coupons.updatePromoCode}
        element={<UpdatePromoCodePage />}
      />
      <Navigate to={routes.ecommerceAdmin.index} />
    </Routes>
  </React.Fragment>
);

export default EcommerceAdminPages;
