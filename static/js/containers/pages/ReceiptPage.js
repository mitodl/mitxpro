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
              <div className="receipt-wrapper">
                <div className="receipt-row p-b-80">
                  <div className="receipt-col">
                    <div className="receipt-logo">
                      <img src="static/images/mitx-pro-logo.png" alt="" />
                    </div>
                    <div className="receipt-mit-info">
                      <p>
                        600 Technology Square
                        <br />
                        NE49-2000
                        <br />
                        Cambridge, MA 02139 USA
                        <br />
                        Support:{" "}
                        <a href="mailto:support@xpro.mit.edu">
                          support@xpro.mit.edu
                        </a>
                        <br />
                        <a
                          target="_blank"
                          href="https://xpro.mit.edu"
                          rel="noreferrer"
                        >
                          xpro.mit.edu
                        </a>
                      </p>
                    </div>
                  </div>
                  <div className="receipt-col p-t-50">
                    <dl>
                      <dt>Order Number:</dt>
                      <dd id="orderNumber">
                        {orderReceipt.order.reference_number}
                      </dd>
                    </dl>
                    <dl>
                      <dt>Order Date:</dt>
                      {orderDate ? (
                        <dd id="orderDate">{formatPrettyDate(orderDate)}</dd>
                      ) : null}
                    </dl>
                    <a href="javascript:window.print();" className="print-btn">
                      <img src="static/images/printer.png" alt="print" />
                    </a>
                  </div>
                </div>
                <h2>Receipt</h2>
                <div className="receipt-row p-b-80">
                  <div className="receipt-col">
                    <h3>Customer Information</h3>
                    <dl>
                      <dt>Name:</dt>
                      <dd id="purchaserName">
                        {orderReceipt.purchaser.first_name}{" "}
                        {orderReceipt.purchaser.last_name}
                      </dd>
                    </dl>
                    {orderReceipt.purchaser.company ? (
                      <dl>
                        <dt>Company Name:</dt>
                        <dd>{orderReceipt.purchaser.company}</dd>
                      </dl>
                    ) : null}
                    <dl>
                      <dt>Address:</dt>
                      <dd>
                        {orderReceipt.purchaser.street_address.map(line => (
                          <div
                            className="value low-line-height"
                            key={line}
                            id={line}
                          >
                            {line}
                          </div>
                        ))}
                        <div
                          className="value low-line-height"
                          id="purchaserState"
                        >
                          {orderReceipt.purchaser.city}, {stateCode}{" "}
                          {orderReceipt.purchaser.postal_code}
                        </div>
                        <div
                          className="value low-line-height"
                          id="purchaserCountry"
                        >
                          {countryName}
                        </div>
                      </dd>
                    </dl>
                    <dl>
                      <dt>Email:</dt>
                      <dd id="purchaserEmail">
                        {orderReceipt.purchaser.email}
                      </dd>
                    </dl>
                  </div>
                  <h3>Payment Information</h3>
                  {orderReceipt.receipt ? (
                    <div className="receipt-col">
                      {orderReceipt.receipt &&
                      orderReceipt.receipt.payment_method === "card" ? (
                          <div>
                            <dl>
                              <dt>Name:</dt>
                              <dd>{orderReceipt.receipt.name}</dd>
                            </dl>
                            <dl>
                              <dt>Payment Method:</dt>
                              <dd id="paymentMethod">
                                {orderReceipt.receipt.card_type
                                  ? `${orderReceipt.receipt.card_type} | `
                                  : null}
                                {orderReceipt.receipt.card_number
                                  ? orderReceipt.receipt.card_number
                                  : null}
                              </dd>
                            </dl>
                          </div>
                        ) : orderReceipt.receipt.payment_method === "paypal" ? (
                          <div>
                            <dl>
                              {orderReceipt.receipt.bill_to_email ? (
                                <dl>
                                  <dt>Email:</dt>
                                  <dd>{orderReceipt.receipt.bill_to_email}</dd>
                                </dl>
                              ) : null}
                            </dl>
                            <dl>
                              <dt>Payment Method:</dt>
                              <dd id="paymentMethod">Paypal</dd>
                            </dl>
                          </div>
                        ) : null}
                    </div>
                  ) : null}
                  {orderReceipt.coupon ? (
                    <div className="receipt-col">
                      <dl>
                        <dt>Discount Code:</dt>
                        <dd id="discountCode">{orderReceipt.coupon}</dd>
                      </dl>
                    </div>
                  ) : null}
                </div>
                <div className="receipt-table-holder">
                  <h3>Product Description</h3>
                  <table className="receipt-table">
                    <thead>
                      <tr>
                        <th>Product Description</th>
                        <th>Quantity</th>
                        <th>Unit Price</th>
                        <th>Discount</th>
                        <th>Total Paid</th>
                      </tr>
                    </thead>
                    <tbody>
                      {orderReceipt.lines.map(line => {
                        const startDate = parseDateString(line.start_date)
                        const endDate = parseDateString(line.end_date)
                        return (
                          <tr key={line.readable_id}>
                            <td>
                              <div>
                                {line.content_title} <br />
                                {line.readable_id} <br />
                                {startDate &&
                                  formatPrettyDate(startDate)} -{" "}
                                {endDate && formatPrettyDate(endDate)}
                                <br />
                                {line.CEUs ? (
                                  <div>CEUs: {line.CEUs}</div>
                                ) : null}
                              </div>
                            </td>
                            <td>
                              <div>{line.quantity}</div>
                            </td>
                            <td>
                              <div>${line.price}</div>
                            </td>
                            <td>
                              <div>${line.discount}</div>
                            </td>
                            <td>
                              <div>${line.total_paid}</div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
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
