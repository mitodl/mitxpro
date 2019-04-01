// @flow
import { getCookie } from "../api"

import type { BasketResponse } from "../../flow/ecommerceTypes"

export default {
  checkoutMutation: () => ({
    url:    "/api/checkout/",
    update: {
      checkout: () => null
    },
    options: {
      method:  "POST",
      force:   true,
      headers: {
        "X-CSRFTOKEN": getCookie("csrftoken")
      }
    }
  }),
  basketQuery: () => ({
    url:       "/api/basket/",
    queryKey:  "get basket",
    transform: (json: BasketResponse) => ({
      basket: json
    }),
    update: {
      basket: (prev: BasketResponse, next: BasketResponse) => next
    }
  }),
  basketMutation: (payload: BasketResponse) => ({
    url:    "/api/basket/",
    update: {
      basket: (prev: BasketResponse, next: BasketResponse) => next
    },
    transform: (json: BasketResponse) => ({
      basket: json
    }),
    body: {
      ...payload
    },
    options: {
      method:  "PATCH",
      force:   true,
      headers: {
        "X-CSRFTOKEN": getCookie("csrftoken")
      }
    }
  })
}
