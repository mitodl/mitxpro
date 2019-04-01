// @flow
/* eslint-disable max-len */
export const CYBERSOURCE_CHECKOUT_RESPONSE = {
  payload: {
    access_key:                   "access_key",
    amount:                       "123.45",
    consumer_id:                  "staff",
    currency:                     "USD",
    locale:                       "en-us",
    override_custom_cancel_page:  "https://micromasters.mit.edu?cancel",
    override_custom_receipt_page: "https://micromasters.mit.edu?receipt",
    profile_id:                   "profile_id",
    reference_number:             "MM-george.local-56",
    signature:                    "56ItDy52E+Ii5aXhiq89OwRsImukIQRQetaHVOM0Fug=",
    signed_date_time:             "2016-08-24T19:07:57Z",
    signed_field_names:
      "access_key,amount,consumer_id,currency,locale,override_custom_cancel_page,override_custom_receipt_page,profile_id,reference_number,signed_date_time,signed_field_names,transaction_type,transaction_uuid,unsigned_field_names",
    transaction_type:     "sale",
    transaction_uuid:     "uuid",
    unsigned_field_names: ""
  },
  url:    "https://testsecureacceptance.cybersource.com/pay",
  method: "POST"
}
