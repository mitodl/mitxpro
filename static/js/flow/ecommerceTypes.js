// @flow
import type { Decimal } from "decimal.js-light"
import type { CourseRun } from "./courseTypes"

export type CheckoutResponse = {
  url: string,
  payload: CheckoutPayload,
  method?: ?string,
  errors?: string|Array<string>
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

export type Company = {
  id: number,
  name: string,
  created_on: Date,
  updated_on: Date,
}

export type CouponPayment = {
  id: number,
  created_on: Date,
  updated_on: Date,
  name: string
}

export type CouponPaymentVersion = {
  id: number,
  payment: CouponPayment,
  created_on: Date,
  updated_on: Date,
  tag: ?string,
  automatic: boolean,
  coupon_type: string,
  num_coupon_codes: number,
  max_redemptions: number,
  max_redemptions_per_user: number,
  amount: number,
  expiration_date: Date,
  activation_date: Date,
  payment_type: ?string,
  payment_transaction: ?string,
  company: ?Company
}

export type Product = {
  id: number,
  title: string,
  product_type: string,
  created_on: Date,
  updated_on: Date,
  object_id: number,
  content_type: number
}
