// @flow
import React from "react"

import MixedLink from "../MixedLink"
import { routes } from "../../lib/urls"
import {
  ALERT_TYPE_TEXT,
  ALERT_TYPE_UNUSED_COUPON,
  ALTER_TYPE_B2B_ORDER_STATUS
} from "../../constants"

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

export const B2BOrderStatusNotification = (props: ComponentProps) => {
  const { dismiss } = props

  return (
    <span>
      Something went wrong. Please contact us at{" "}
      <a
        href="https://xpro.zendesk.com/hc/en-us/requests/new"
        onClick={dismiss}
        className="alert-link"
      >
        Customer Support
      </a>
      .
    </span>
  )
}

export const notificationTypeMap = {
  [ALERT_TYPE_TEXT]:             TextNotification,
  [ALERT_TYPE_UNUSED_COUPON]:    UnusedCouponNotification,
  [ALTER_TYPE_B2B_ORDER_STATUS]: B2BOrderStatusNotification
}
