// @flow
/* global SETTINGS: false */

import React from "react"
import DocumentTitle from "react-document-title"
import { RECEIPT_PAGE_TITLE } from "../../constants"
import { compose } from "redux"
import { connect } from "react-redux"
import { connectRequest } from "redux-query"
import moment from "moment"
import { pathOr } from "ramda"

import queries from "../../lib/queries"
import { formatPrettyDate, parseDateString } from "../../lib/util"

import type Moment from "moment"
import type { Match } from "react-router"
import type { OrderReceiptResponse } from "../../flow/ecommerceTypes"
import type { Country, CurrentUser } from "../../flow/authTypes"

type Props = {
  isLoading: boolean,
  orderReceipt: OrderReceiptResponse,
  countries: Array<Country>,
  match: Match,
  currentUser: CurrentUser,
  forceRequest: () => Promise<*>
}

export class ReceiptPage extends React.Component<Props> {
  async componentDidMount() {
    // If we have a preloaded order but it's not the one we should display, force a fetch
    if (
      this.props.orderReceipt &&
      this.props.orderReceipt.order.id !==
        parseInt(this.props.match.params.orderId)
    ) {
      await this.props.forceRequest()
    }
  }

  async componentDidUpdate(prevProps: Props) {
    if (prevProps.match.params.orderId !== this.props.match.params.orderId) {
      await this.props.forceRequest()
    }
  }

  render() {
    const {
      orderReceipt,
      isLoading,
      countries,
      match,
      currentUser
    } = this.props
    let orderDate = null
    let stateCode = null
    let countryName = null

    if (orderReceipt) {
      orderDate = parseDateString(orderReceipt.order.created_on)

      if (countries) {
        const country = countries.find(
          element => element.code === orderReceipt.purchaser.country
        )
        if (country) {
          countryName = country.name
        }
      }

      if (orderReceipt.purchaser.state_or_territory) {
        stateCode = orderReceipt.purchaser.state_or_territory.split("-").pop()
      }
    }

    return (
      <React.Fragment>
        <DocumentTitle title={`${SETTINGS.site_name} | ${RECEIPT_PAGE_TITLE}`}>
          <div className="user-dashboard container">
            {currentUser.is_anonymous && (
              <div className="row">
                You must be logged in to view order receipts.
              </div>
            )}
            {currentUser.is_authenticated && isLoading && (
              <div className="row">
                <div className="header col-12">
                  <h1>Loading...</h1>
                </div>
              </div>
            )}
            {currentUser.is_authenticated && !isLoading && !orderReceipt && (
              <div className="row">
                <div className="header col-12">
                  <h1>Could not find order with ID: {match.params.orderId}</h1>
                </div>
              </div>
            )}
            {currentUser.is_authenticated && !isLoading && orderReceipt && (
              <div id="wrapper">
                <div className="receipt-wrapper">
                  <div className="print-row">
                    <a href="javascript:window.print();">
                      Print <img src="/static/images/printer.png" alt="print" />
                    </a>
                  </div>
                  <div className="rec-logo">
                    <img
                      src="/static/images/mitx-pro-logo.png"
                      alt="MIT xPro"
                    />
                  </div>
                  <h1>Receipt</h1>
                  <div className="section-info gray">
                    <div className="container section-holder">
                      <div className="row no-gutters">
                        <div className="col-12">
                          <h2>Order Information</h2>
                        </div>
                      </div>
                      <div className="row no-gutters">
                        <div className="col-lg-2 col-md-3 col-sm-4">
                          <p className="label">Order Date:</p>
                        </div>
                        <div className="col-lg-10 col-md-9 col-sm-8">
                          {orderDate ? (
                            <p className="value" id="orderDate">
                              {formatPrettyDate(orderDate)}
                            </p>
                          ) : null}
                        </div>
                      </div>
                      <div className="row no-gutters">
                        <div className="col-lg-2 col-md-3 col-sm-4">
                          <p className="label">Order Number:</p>
                        </div>
                        <div className="col-lg-10 col-md-9 col-sm-8">
                          {orderDate ? (
                            <p className="value" id="orderNumber">
                              {orderReceipt.order.reference_number}
                            </p>
                          ) : null}
                        </div>
                      </div>
                      <div className="row no-gutters">
                        <div className="col-lg-2 col-md-3 col-sm-4">
                          <p className="label">Order Total:</p>
                        </div>
                        <div className="col-lg-10 col-md-9 col-sm-8">
                          {orderDate ? (
                            <p className="value" id="orderTotal">
                              $
                              {orderReceipt.lines.reduce(
                                (total, line) =>
                                  total + parseFloat(line.total_paid),
                                0.0
                              )}
                            </p>
                          ) : null}
                        </div>
                      </div>
                    </div>
                    {orderReceipt.lines.map(line => {
                      const startDate = parseDateString(line.start_date)
                      const endDate = parseDateString(line.end_date)
                      return (
                        <div
                          key={line.readable_id}
                          className="container section-holder pt-0"
                        >
                          <hr />
                          <div className="row no-gutters">
                            <div className="col-lg-2 col-md-3 col-sm-4">
                              <p className="label">Order Item:</p>
                            </div>
                            <div className="col-lg-4 col-md-3 col-sm-8">
                              <p className="value">{line.content_title}</p>
                            </div>
                            <div className="col-lg-6 col-md-6">
                              <div className="row no-gutters label-table d-none d-md-flex">
                                <div className="col-lg-3 col-md-3 col-sm-6">
                                  <p className="low-line-height label">
                                    Quantity
                                  </p>
                                  <p className="low-line-height value">
                                    {line.quantity}
                                  </p>
                                </div>
                                <div className="col-lg-3 col-md-3 col-sm-6">
                                  <p className="low-line-height label">
                                    Unit Price
                                  </p>
                                  <p className="low-line-height value">
                                    ${line.price}
                                  </p>
                                </div>
                                <div className="col-lg-3 col-md-3 col-sm-6">
                                  <p className="low-line-height label">
                                    Discount
                                  </p>
                                  <p className="low-line-height value">
                                    ${line.discount}
                                  </p>
                                </div>
                                <div className="col-lg-3 col-md-3 col-sm-6">
                                  <p className="low-line-height label">
                                    Total Paid
                                  </p>
                                  <p className="low-line-height value">
                                    ${line.total_paid}
                                  </p>
                                </div>
                              </div>
                            </div>
                          </div>
                          <div className="row no-gutters d-md-none">
                            <div className="col-sm-4">
                              <p className="label">Quantity:</p>
                            </div>
                            <div className="col">
                              <p className="value">{line.quantity}</p>
                            </div>
                          </div>
                          <div className="row no-gutters d-md-none">
                            <div className="col-sm-4">
                              <p className="label">Unit Price:</p>
                            </div>
                            <div className="col">
                              <p className="value">${line.price}</p>
                            </div>
                          </div>
                          <div className="row no-gutters d-md-none">
                            <div className="col-sm-4">
                              <p className="label">Discount:</p>
                            </div>
                            <div className="col">
                              <p className="value">${line.discount}</p>
                            </div>
                          </div>
                          <div className="row no-gutters d-md-none">
                            <div className="col-sm-4">
                              <p className="label">Total Paid:</p>
                            </div>
                            <div className="col">
                              <p className="value">${line.total_paid}</p>
                            </div>
                          </div>
                          <div className="row no-gutters">
                            <div className="col-lg-2 col-md-3 col-sm-4">
                              <p className="label">Product Number:</p>
                            </div>
                            <div className="col">
                              <p className="value">{line.readable_id}</p>
                            </div>
                          </div>
                          <div className="row no-gutters">
                            <div className="col-lg-2 col-md-3 col-sm-4">
                              <p className="label">Dates:</p>
                            </div>
                            <div className="col-lg-4 col-md-4 col-sm-5">
                              <p className="value">
                                {startDate && formatPrettyDate(startDate)} -{" "}
                                {endDate && formatPrettyDate(endDate)}
                              </p>
                            </div>
                            <div className="col" />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                  <div className="section-info">
                    <div className="container section-holder">
                      <div className="row no-gutters">
                        <div className="col">
                          <h2>Customer Information</h2>
                        </div>
                      </div>
                      <div className="row no-gutters">
                        <div className="col-lg-2 col-md-3 col-sm-4">
                          <p className="label">Name:</p>
                        </div>
                        <div className="col-lg-10 col-md-9 col-sm-8">
                          <p className="value" id="purchaserName">
                            {orderReceipt.purchaser.first_name}{" "}
                            {orderReceipt.purchaser.last_name}
                          </p>
                        </div>
                      </div>
                      <div className="row no-gutters">
                        <div className="col-lg-2 col-md-3 col-sm-4">
                          <p className="label">Email Address:</p>
                        </div>
                        <div className="col-lg-10 col-md-9 col-sm-8">
                          <p className="value" id="purchaserEmail">
                            {orderReceipt.purchaser.email}
                          </p>
                        </div>
                      </div>
                      <div className="row no-gutters">
                        <div className="col-lg-2 col-md-3 col-sm-4">
                          <p className="label">Address:</p>
                        </div>
                        <div className="col-lg-10 col-md-9 col-sm-8">
                          {orderReceipt.purchaser.street_address.map(line => (
                            <p
                              className="value low-line-height"
                              key={line}
                              id={line}
                            >
                              {line}
                            </p>
                          ))}
                          <p
                            className="value low-line-height"
                            id="purchaserState"
                          >
                            {orderReceipt.purchaser.city}, {stateCode}{" "}
                            {orderReceipt.purchaser.postal_code}
                          </p>
                          <p
                            className="value low-line-height"
                            id="purchaserCountry"
                          >
                            {countryName}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                  {orderReceipt.coupon || orderReceipt.receipt ? (
                    <div className="section-info gray">
                      <div className="container section-holder">
                        <div className="row no-gutters">
                          <div className="col">
                            <h2>Payment Information</h2>
                          </div>
                        </div>
                        {orderReceipt.receipt ? (
                          <div className="row no-gutters">
                            <div className="col-lg-2 col-md-3 col-sm-4">
                              <p className="label">Payment Method:</p>
                            </div>
                            <div className="col-lg-10 col-md-9 col-sm-8">
                              <p className="value" id="paymentMethod">
                                {orderReceipt.receipt.card_type
                                  ? `${orderReceipt.receipt.card_type} | `
                                  : null}
                                {orderReceipt.receipt.card_number
                                  ? orderReceipt.receipt.card_number
                                  : null}
                              </p>
                            </div>
                          </div>
                        ) : null}
                        {orderReceipt.coupon ? (
                          <div className="row no-gutters">
                            <div className="col-lg-2 col-md-3 col-sm-4">
                              <p className="label">Discount Code:</p>
                            </div>
                            <div className="col-lg-10 col-md-9 col-sm-8">
                              <p className="value" id="discountCode">
                                {orderReceipt.coupon}
                              </p>
                            </div>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  ) : null}
                  <div className="rec-footer">
                    <div className="rec-footer-top">
                      <div className="rec-footer-info">
                        <div className="rec-footer-logo">
                          <img src="/static/images/mit-dark.png" alt="MIT" />
                        </div>
                        <div className="info">
                          <p>
                            MIT
                            <br />
                            Massachusetts Institute of Technology
                            <br />
                            77 Massachusetts Avenue
                            <br />
                            Cambridge, MA 02139
                          </p>
                        </div>
                      </div>
                    </div>
                    <span className="rec-copyright">
                      © 2019 All rights reserved. MIT xPRO.
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </DocumentTitle>
      </React.Fragment>
    )
  }
}

const mapStateToProps = state => ({
  currentUser:  state.entities.currentUser,
  countries:    state.entities.countries,
  orderReceipt: state.entities.orderReceipt,
  isLoading:
    pathOr(true, ["queries", "countries", "isPending"], state) ||
    pathOr(true, ["queries", "orderReceipt", "isPending"], state)
})

const mapPropsToConfigs = props => [
  queries.users.countriesQuery(),
  queries.ecommerce.orderReceipt(props.match.params.orderId)
]

export default compose(
  connect(mapStateToProps),
  connectRequest(mapPropsToConfigs)
)(ReceiptPage)
