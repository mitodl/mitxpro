// @flow
import type { Course } from "./courseTypes"
import {PRODUCT_TYPE_COURSE, PRODUCT_TYPE_COURSERUN, PRODUCT_TYPE_PROGRAM} from "../constants"

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
  type: PRODUCT_TYPE_COURSERUN | PRODUCT_TYPE_COURSE | PRODUCT_TYPE_PROGRAM,
  courses: Array<Course>,
  thumbnail_url: string,
  price: string,
  description: string,
  object_id: number,
  product_id: number,
  id: number,
  run_ids: Array<number>,
}

export type CouponSelection = {
  code: string,
  amount: string,
  targets: Array<number>
}

export type DataConsentUser = {
  agreement: number,
  coupon: number,
  consent_data: string,
  id: number,
}

export type BasketResponse = {
  items: Array<BasketItem>,
  coupons: Array<CouponSelection>,
  data_consents: Array<DataConsentUser>
}

type BasketItemPayload = {
  id: number,
  run_ids?: Array<number>,
}

export type BasketPayload = {
  items?: Array<BasketItemPayload>,
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

export type Coupon = {
  name: string,
  coupon_code: string,
  enabled: boolean,
  created_on: Date,
  updated_on: Date
}

export type Product = {
  id: number,
  title: string,
  product_type: string,
  created_on: Date,
  updated_on: Date,
  object_id: number,
  content_type: number,
}

export type ProductMap = {
  [PRODUCT_TYPE_COURSERUN | PRODUCT_TYPE_COURSE | PRODUCT_TYPE_PROGRAM]: Array<Product>,
}

export type BulkCouponPayment = {
  id: number,
  name: string,
  version: CouponPaymentVersion,
  products: Array<Product>,
  created_on: Date,
  updated_on: Date
}

export type BulkCouponPaymentsResponse = Array<BulkCouponPayment>

export type BulkCouponSendResponse = {
  emails: Array<string>
}
