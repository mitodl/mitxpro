/* global SETTINGS: false */
// @flow
import { assert } from "chai"
import sinon from "sinon"
// $FlowFixMe: flow doesn't see fn
import { fn as momentProto } from "moment"
import qs from "query-string"
import casual from "casual-browserify"

import B2BReceiptPage, {
  B2BReceiptPage as InnerB2BReceiptPage
} from "./B2BReceiptPage"

import * as utilFuncs from "../../../lib/util"
import IntegrationTestHelper from "../../../util/integration_test_helper"
import { makeB2BOrderStatus } from "../../../factories/ecommerce"
import { formatPrice } from "../../../lib/ecommerce"

describe("B2BReceiptPage", () => {
  let helper, renderPage, orderStatus, orderHash

  beforeEach(() => {
    orderHash = casual.uuid
    helper = new IntegrationTestHelper()
    orderStatus = { ...makeB2BOrderStatus(), status: "fulfilled" }
    helper.handleRequestStub
      .withArgs(`/api/b2b/orders/${orderHash}/status/`, "GET")
      .returns({
        body:   orderStatus,
        status: 200
      })
    renderPage = helper.configureHOCRenderer(
      B2BReceiptPage,
      InnerB2BReceiptPage,
      {
        entities: {
          b2b_order_status: orderStatus
        }
      },
      {
        location: {
          search: qs.stringify({ hash: orderHash })
        }
      }
    )
  })

  afterEach(() => {
    helper.cleanup()
  })

  it("renders a receipt", async () => {
    const { inner } = await renderPage()
    assert.isTrue(
      inner
        .find(".course-or-program")
        .text()
        .includes(orderStatus.product_version.content_title)
    )
    assert.isTrue(
      inner
        .find(".course-or-program")
        .text()
        .includes(orderStatus.product_version.readable_id)
    )
    assert.isTrue(
      inner
        .find(".seats")
        .text()
        .includes(
          `${orderStatus.num_seats} (at ${formatPrice(
            orderStatus.item_price
          )} per seat)`
        )
    )
    assert.isTrue(
      inner
        .find(".email")
        .text()
        .includes(orderStatus.email)
    )
    const summaryProps = inner.find("B2BPurchaseSummary").props()
    assert.equal(String(summaryProps.itemPrice), orderStatus.item_price)
    assert.equal(String(summaryProps.totalPrice), orderStatus.total_price)
    assert.equal(summaryProps.numSeats, orderStatus.num_seats)
  })

  it("has a link to download enrollment codes", async () => {
    const { inner } = await renderPage()
    const link = inner.find(".enrollment-codes-link")
    assert.equal(link.prop("href"), `/api/b2b/orders/${orderHash}/codes/`)
    assert.isTrue(link.text().startsWith("Download codes"))
  })

  it("reads from the order status API", async () => {
    const newOrderStatus = makeB2BOrderStatus()
    const newHash = "a-different-order-hash"
    helper.handleRequestStub
      .withArgs(`/api/b2b/orders/${newHash}/status/`, "GET")
      .returns({
        status: 200,
        body:   newOrderStatus
      })

    const { wrapper } = await renderPage(
      {},
      {
        location: {
          search: qs.stringify({ hash: newHash })
        }
      }
    )
    sinon.assert.calledWith(
      helper.handleRequestStub,
      `/api/b2b/orders/${newHash}/status/`,
      "GET"
    )
    assert.equal(wrapper.prop("orderStatus"), newOrderStatus)
  })

  //
  ;[true, false].forEach(outOfTime => {
    it(`if a run or program is not immediately found it waits 3 seconds and ${
      outOfTime ? "errors" : "force reloads"
    }`, async () => {
      let waitResolve = null
      const waitPromise = new Promise(resolve => {
        waitResolve = resolve
      })
      const waitStub = helper.sandbox
        .stub(utilFuncs, "wait")
        .returns(waitPromise)

      orderStatus.status = "created"
      const fulfilledOrderStatus = {
        ...orderStatus,
        status: "fulfilled"
      }
      const { store } = await renderPage()
      helper.handleRequestStub.resetHistory()

      sinon.assert.calledWith(waitStub, 3000)
      helper.handleRequestStub
        .withArgs(`/api/b2b/orders/${orderHash}/status/`, "GET")
        .returns({
          body:   fulfilledOrderStatus,
          status: 200
        })
      helper.sandbox.stub(momentProto, "isBefore").returns(!outOfTime)
      // $FlowFixMe
      waitResolve()
      await waitPromise

      if (outOfTime) {
        assert.deepEqual(store.getState().ui.userNotifications, {
          "b2b-order-status": {
            color: "danger",
            type:  "b2b-order-status"
          }
        })
      } else {
        sinon.assert.calledWith(
          helper.handleRequestStub,
          `/api/b2b/orders/${orderHash}/status/`
        )
      }
    })
  })
})
