// @flow
import React from "react"

import Expandable from "./Expandable"

type Props = {
  className?: string
}
const B2BCheckoutExplanation = ({ className }: Props) => (
  <div className={`container b2b-explanation ${className ? className : ""}`}>
    <div className="row">
      <div className="col-lg-8 ">
        <Expandable className="last-expandable" title="How It Works">
          <p>Step 1 - Purchase unique "enrollment codes" for your learners.</p>
          <p>Step 2 - Distribute enrollment codes to each of your learners.</p>
          <p>
            Step 3 - Your learners use the enrollment code to enroll in the
            course.
          </p>
        </Expandable>
      </div>
    </div>
  </div>
)
export default B2BCheckoutExplanation
