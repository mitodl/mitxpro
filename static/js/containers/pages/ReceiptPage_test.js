// @flow
import { assert } from "chai"
import sinon from "sinon"

import ReceiptPage, { ReceiptPage as InnerReceiptPage } from "./ReceiptPage"
import {
  makeAnonymousUser,
  makeCountries,
  makeUser
} from "../../factories/user"
import IntegrationTestHelper from "../../util/integration_test_helper"
import { formatPrettyDate, parseDateString } from "../../lib/util"

describe("ReceiptPage", () => {
  let helper, renderPage
  const user = makeUser()
  const countries = makeCountries()
  const receiptObject = {
    purchaser: {
      first_name:         "John",
      last_name:          "Doe",
      street_address:     ["Ashley-Street"],
      city:               "Montobello",
      state_or_territory: "US-CA",
      country:            "US",
      postal_code:        "90640",
      company:            "ABC",
      email:              "john.doe@acme.com"
    },
    lines: [
      {
        quantity:      1,
        total_paid:    "200",
        discount:      "200",
        price:         "400",
        content_title: "Demon Course",
        readable_id:   "course-v1:edX+DemoX+Demo_Course",
        start_date:    "2018-04-30T00:00:00Z",
        end_date:      "2018-07-02T00:00:00Z"
      }
    ],
    coupon: "50OFF",
    order:  {
      id:               1,
      created_on:       "2019-10-09T09:47:09.219354Z",
      reference_number: "xpro-b2c-dev-1"
    },
    receipt: {
      bill_to_forename: "John",
      card_number:      "xxxxxxxxxxxx1234",
      card_type:        "Visa",
      payment_method:   "card"
    }
  }

  beforeEach(() => {
    helper = new IntegrationTestHelper()

    renderPage = helper.configureHOCRenderer(
      ReceiptPage,
      InnerReceiptPage,
      {
        entities: {
          currentUser:  user,
          countries:    countries,
          orderReceipt: receiptObject
        },
        queries: {
          countries: {
            isPending: false
          },
          orderReceipt: {
            isPending: false
          }
        }
      },
      {
        match: {
          params: {
            orderId: 1
          }
        }
      }
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("renders the page with a receipt for a logged in user", async () => {
    const { inner } = await renderPage()
    assert.isTrue(inner.find(".receipt-wrapper").exists())
  })

  it("renders the receipt with correct information for a logged in user", async () => {
    const { inner } = await renderPage()
    assert.isTrue(inner.find(".receipt-wrapper").exists())
    assert.equal(
      inner.find("#orderNumber").text(),
      receiptObject.order.reference_number
    )

    const dateString = parseDateString(receiptObject.order.created_on)

    // $FlowFixMe: Flow doesn't know we will always have a Moment returned from pareDateString here
    const prettyDate = formatPrettyDate(dateString)
    assert.equal(inner.find("#orderDate").text(), prettyDate)

    assert.equal(
      inner.find("#purchaserName").text(),
      `${receiptObject.purchaser.first_name} ${
        receiptObject.purchaser.last_name
      }`
    )
    assert.equal(
      inner.find("#purchaserEmail").text(),
      receiptObject.purchaser.email
    )
    receiptObject.purchaser.street_address.map(item =>
      assert.equal(inner.find(`#${item}`).text(), item)
    )
    assert.equal(
      inner.find("#purchaserState").text(),
      `${
        receiptObject.purchaser.city
      }, ${receiptObject.purchaser.state_or_territory.split("-").pop()} ${
        receiptObject.purchaser.postal_code
      }`
    )
    // $FlowFixMe: Flow doesn't know we will definitely find a match here
    const countryName = countries.find(
      country => country.code === receiptObject.purchaser.country
    ).name
    assert.equal(inner.find("#purchaserCountry").text(), countryName)
    if (inner.find("#paymentMethod").text() === "card") {
      assert.equal(
        inner.find("#paymentMethod").text(),
        `${receiptObject.receipt.card_type} | ${
          receiptObject.receipt.card_number
        }`
      )
    }
    assert.equal(inner.find("#discountCode").text(), receiptObject.coupon)
  })

  it("renders the page with a login message for an anonymous user", async () => {
    const { inner } = await renderPage(
      {
        entities: {
          currentUser: makeAnonymousUser(),
          countries:   countries
        }
      },
      {
        match: {
          params: {
            orderId: 1
          }
        }
      }
    )
    assert.isFalse(inner.find(".receipt-wrapper").exists())
    assert.isTrue(
      inner
        .find(".user-dashboard")
        .text()
        .includes("You must be logged in to view order receipts.")
    )
  })
})
