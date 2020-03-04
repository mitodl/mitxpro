// @flow
import React from "react"

import Expandable from "./Expandable"

type Props = {
  className?: string
}
const B2BReceiptExplanation = ({ className }: Props) => (
  <div className={`container b2b-explanation ${className ? className : ""}`}>
    <div className="row">
      <div className="col-lg-12">
        <Expandable className="last-expandable" title="Enrollment Codes">
          <ul>
            <li>
              Enrollment codes act as a confirmation of purchase and gives the
              recipient access to the course.
            </li>
            <li>
              The recipient enters the enrollment code at checkout, instead of
              paying for the course.
            </li>
          </ul>
        </Expandable>
      </div>
    </div>
  </div>
)
export default B2BReceiptExplanation
