// @flow
import React from "react"

import Expandable from "./Expandable"

type Props = {
  alreadyPaid: boolean,
  className?: string
}
const B2BExplanation = ({ alreadyPaid, className }: Props) => (
  <div className={`container b2b-explanation ${className ? className : ""}`}>
    <div className="row">
      <div className="col-lg-8">
        {alreadyPaid ? (
          <Expandable title="Enrollment Codes">
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
        ) : (
          <Expandable title="How It Works">
            <p>
              Step 1 - Purchase unique "enrollment codes" for your learners.
            </p>
            <p>
              Step 2 - Distribute enrollment codes to each of your learners.
            </p>
            <p>
              Step 3 - Your learners use the enrollment code to enroll in the
              course.
            </p>
          </Expandable>
        )}

        <Expandable title="Purchase Agreement" className="last-expandable">
          <ul>
            <li>Each enrollment code can be used only one time.</li>
            <li>
              You are responsible for distributing codes to your learners in
              your organization.
            </li>
            <li>
              Each code will expire in one year from the date of purchase or, if
              earlier, once the course is closed.
            </li>
            <li>You may not resell codes to third parties.</li>
            <li>
              All xPRO business sales are final and not eligible for refunds.
            </li>
          </ul>
        </Expandable>
      </div>
    </div>
  </div>
)
export default B2BExplanation
