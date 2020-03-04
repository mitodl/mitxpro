/* global SETTINGS: false */
// @flow
import React from "react"
import { connect } from "react-redux"
import { compose } from "redux"
import { connectRequest } from "redux-query"
import qs from "query-string"
import moment from "moment"
import Decimal from "decimal.js-light"

import B2BPurchaseSummary from "../../../components/B2BPurchaseSummary"

import queries from "../../../lib/queries"
import { addUserNotification } from "../../../actions"
import { wait } from "../../../lib/util"
import { formatPrice } from "../../../lib/ecommerce"
import { ALERT_TYPE_TEXT } from "../../../constants"
import { bulkReceiptCsvUrl } from "../../../lib/urls"

import type { B2BOrderStatus } from "../../../flow/ecommerceTypes"
import type { Location } from "react-router"
import type Moment from "moment"
import B2BExplanation from "../../../components/B2BExplanation"

type Props = {
  addUserNotification: Function,
  orderStatus: B2BOrderStatus,
  location: Location,
  forceRequest: () => Promise<void>,
  requestPending: boolean
}
type State = {
  now: Moment,
  timeoutActive: boolean
}

const NUM_MINUTES_TO_POLL = 2
const NUM_MILLIS_PER_POLL = 3000

export class B2BReceiptPage extends React.Component<Props, State> {
  state = {
    now:           moment(),
    timeoutActive: false
  }

  componentDidMount() {
    this.handleOrderStatus()
  }

  componentDidUpdate(prevProps: Props) {
    // This is meant to be an identity check, not a deep equality check. This shows whether we received an update
    // for enrollments based on the forceReload
    if (prevProps.orderStatus !== this.props.orderStatus) {
      this.handleOrderStatus()
    }
  }

  handleOrderStatus = async () => {
    const { orderStatus } = this.props

    if (!orderStatus) {
      // wait until we have a order status
      return
    }

    this.handleOrderPending()
  }

  handleOrderPending = async () => {
    const { addUserNotification, orderStatus, forceRequest } = this.props
    const { timeoutActive, now: initialTime } = this.state

    if (timeoutActive) {
      return
    }

    if (orderStatus.status === "fulfilled") {
      // all set
      return
    }

    this.setState({ timeoutActive: true })
    await wait(NUM_MILLIS_PER_POLL)
    this.setState({ timeoutActive: false })

    const deadline = moment(initialTime).add(NUM_MINUTES_TO_POLL, "minutes")
    const now = moment()
    if (now.isBefore(deadline)) {
      await forceRequest()
    } else {
      addUserNotification({
        "b2b-order-status": {
          type:  ALERT_TYPE_TEXT,
          color: "danger",
          props: {
            text: `Something went wrong. Please contact support at ${SETTINGS.support_email}.`
          }
        }
      })
    }
  }

  render() {
    const {
      orderStatus,
      location: { search }
    } = this.props

    const hash = qs.parse(search).hash

    if (!orderStatus || orderStatus.status !== "fulfilled") {
      return <div className="b2b-receipt-page">Loading...</div>
    }

    const totalPrice = new Decimal(orderStatus.total_price)
    const itemPrice = new Decimal(orderStatus.item_price)

    const {
      num_seats: numSeats,
      email,
      contract_number: contractNumber,
      product_version: { content_title: title, readable_id: readableId }
    } = orderStatus

    return (
      <React.Fragment>
        <div className="b2b-receipt-page container">
          <div className="row">
            <div className="col-lg-12">
              <div className="title">Bulk Seats Receipt</div>
            </div>
          </div>
          <div className="row">
            <div className="col-lg-8">
              <p>
                Thank you! You have purchased one or more seats for your team.
              </p>
              <h3>Purchase Summary (Order Number):</h3>
              <p className="course-or-program">
                <span className="description">Course or program:</span>
                {title}
                <span className="description">{readableId}</span>
              </p>
              <p className="seats">
                <span className="description">Seats:</span>
                {numSeats} (at {formatPrice(itemPrice)} per seat)
              </p>
              <p className="email">
                <span className="description">Email Address:</span>
                {email}
              </p>
              {contractNumber && (
                <p className="contract-number">
                  <span className="description">Contract Number:</span>
                  {contractNumber}
                </p>
              )}
              If you encounter any issues please contact{" "}
              <a href="https://xpro.zendesk.com/hc/requests/new">
                customer support
              </a>
              .
            </div>
            <div className="col-lg-4">
              <B2BPurchaseSummary
                itemPrice={itemPrice}
                totalPrice={totalPrice}
                discount={orderStatus.discount}
                alreadyPaid={true}
                numSeats={numSeats}
              />
              <a
                href={bulkReceiptCsvUrl(hash)}
                className="enrollment-codes-link"
              >
                Download codes <i className="material-icons">save_alt</i>
              </a>
            </div>
          </div>
        </div>
        <B2BExplanation
          alreadyPaid={true}
          className="b2b-receipt-explanation"
        />
      </React.Fragment>
    )
  }
}

const mapStateToProps = state => ({
  orderStatus: state.entities.b2b_order_status
})

const mapDispatchToProps = {
  addUserNotification
}

const mapPropsToConfig = props => [
  queries.ecommerce.b2bOrderStatus(qs.parse(props.location.search).hash)
]

export default compose(
  connect(
    mapStateToProps,
    mapDispatchToProps
  ),
  connectRequest(mapPropsToConfig)
)(B2BReceiptPage)
