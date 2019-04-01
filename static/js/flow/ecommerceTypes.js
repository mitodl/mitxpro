// @flow
import type { Decimal } from "decimal.js-light"
import type { CourseRun } from "./courseTypes"

export type CheckoutResponse = {
  url: string,
  payload: CheckoutPayload,
  method?: ?string
};

export type CheckoutPayload = {
  "access_key": string,
  "amount": string,
  "consumer_id": string,
  "currency": string,
  "locale": string,
  "override_custom_cancel_page": string,
  "override_custom_receipt_page": string,
  "profile_id": string,
  "reference_number": string,
  "signature": string,
  "signed_date_time": string,
  "signed_field_names": string,
  "transaction_type": string,
  "transaction_uuid": string,
  "unsigned_field_names": string,
};

export type BasketItem = {
  type: "courserun" | "course" | "program",
  course_runs: Array<CourseRun>,
  thumbnail_url: string,
  price: Decimal,
  description: string,
  id: number,
}

export type Coupon = {
  code: string,
  amount: Decimal,
  targets: Array<number>
}

export type BasketResponse = {
  items: Array<BasketItem>,
  coupons: Array<Coupon>
}

export type BasketPayload = {
  items?: Array<{ id: number }>,
  coupons?: Array<{ code: string }>
}
