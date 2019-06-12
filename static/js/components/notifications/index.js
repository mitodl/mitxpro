// @flow
import React from "react"

import MixedLink from "../MixedLink"
import { routes } from "../../lib/urls"
import { ALERT_TYPE_TEXT, ALERT_TYPE_UNUSED_COUPON } from "../../constants"

import type {
  TextNotificationProps,
  UnusedCouponNotificationProps
} from "../../reducers/notifications"

type ComponentProps = {
  dismiss: Function
}

export const TextNotification = (
  props: TextNotificationProps & ComponentProps
) => <span>{props.text}</span>

export const UnusedCouponNotification = (
  props: UnusedCouponNotificationProps & ComponentProps
) => {
  const { productId, couponCode, dismiss } = props

  return (
    <span>
      You have an unused coupon.{" "}
      <MixedLink
        dest={`${routes.checkout}?product=${productId}&code=${couponCode}`}
        onClick={dismiss}
        className="alert-link"
      >
        Checkout now
      </MixedLink>{" "}
      to redeem it.
    </span>
  )
}

export const notificationTypeMap = {
  [ALERT_TYPE_TEXT]:          TextNotification,
  [ALERT_TYPE_UNUSED_COUPON]: UnusedCouponNotification
}
