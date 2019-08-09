/* global SETTINGS: false */
import React from "react"
import DocumentTitle from "react-document-title"
import { VIEW_PROFILE_PAGE_TITLE } from "../../../constants"
import { connectRequest } from "redux-query"
import { compose } from "redux"
import { connect } from "react-redux"
import type { RouterHistory } from "react-router"
import moment from "moment"
import { find, fromPairs, join, propEq } from "ramda"
import { createStructuredSelector } from "reselect"

import {
  EMPLOYMENT_EXPERIENCE,
  EMPLOYMENT_SIZE,
  GENDER_CHOICES
} from "../../../constants"
import queries from "../../../lib/queries"
import { currentUserSelector } from "../../../lib/queries/users"
import { routes } from "../../../lib/urls"

import type { Country, CurrentUser } from "../../../flow/authTypes"

type StateProps = {|
  currentUser: ?CurrentUser,
  countries: Array<Country>
|}

type ProfileProps = {
  history: RouterHistory
}

type Props = {|
  ...ProfileProps,
  ...StateProps
|}

export class ViewProfilePage extends React.Component<Props> {
  render() {
    const { currentUser, countries, history } = this.props
    return (
      <DocumentTitle
        title={`${SETTINGS.site_name} | ${VIEW_PROFILE_PAGE_TITLE}`}
      >
        <div className="container auth-page registration-page">
          <div className="auth-header row d-flex  align-items-center justify-content-between flex-nowrap">
            <div className="col-auto flex-shrink-1">
              <h1>Profile</h1>
            </div>
            <div>{`Build your profile on ${SETTINGS.site_name}`}.</div>
          </div>
          <div className="auth-card card-shadow row">
            <div className="container profile-container ">
              <div className="row">
                {currentUser.is_authenticated ? (
                  <div className="col-12 auth-form">
                    <div className="row">
                      <div className="col-2 profile" />
                      <div className="col-10 d-flex align-items-center">
                        <h3 className="align-middle">
                          {currentUser.legal_address.first_name}{" "}
                          {currentUser.legal_address.last_name}
                        </h3>
                      </div>
                    </div>
                    <div className="row submit-row no-gutters justify-content-end">
                      <button
                        type="submit"
                        onClick={() => {
                          history.push(routes.profile.update)
                        }}
                        className="btn btn-primary btn-light-blue"
                      >
                        Edit Profile
                      </button>
                    </div>
                    <div className="row">
                      <div className="col">Gender</div>
                      <div className="col">
                        {fromPairs(GENDER_CHOICES)[currentUser.profile.gender]}
                      </div>
                    </div>
                    <div className="row">
                      <div className="col">Year of Birth</div>
                      <div className="col">
                        {currentUser.profile.birth_year}
                      </div>
                    </div>
                    <div className="row">
                      <div className="col">Joined</div>
                      <div className="col">
                        {moment(currentUser.created_on).format("MMMM YYYY")}
                      </div>
                    </div>
                    <div className="row">
                      <div className="col">Address</div>
                      <div className="col">
                        {join(", ", currentUser.legal_address.street_address)},{" "}
                        {currentUser.legal_address.city}
                        {currentUser.legal_address.postal_code
                          ? ` ${currentUser.legal_address.state_or_territory.slice(
                            3
                          )} ${currentUser.legal_address.postal_code}`
                          : ""}
                      </div>
                    </div>
                    {countries && currentUser.legal_address.country ? (
                      <div className="row">
                        <div className="col">Country</div>
                        <div className="col">
                          {
                            find(
                              propEq("code", currentUser.legal_address.country),
                              countries
                            ).name
                          }
                        </div>
                      </div>
                    ) : null}
                    {countries &&
                    currentUser.legal_address.state_or_territory ? (
                        <div className="row">
                          <div className="col">State/Province/Region</div>
                          <div className="col">
                            {
                              find(
                                propEq(
                                  "code",
                                  currentUser.legal_address.state_or_territory
                                ),
                                find(
                                  propEq(
                                    "code",
                                    currentUser.legal_address.country
                                  ),
                                  countries
                                ).states
                              ).name
                            }
                          </div>
                        </div>
                      ) : null}
                    <div className="row">
                      <div className="col">Company</div>
                      <div className="col">{currentUser.profile.company}</div>
                    </div>
                    <div className="row">
                      <div className="col">Job Title</div>
                      <div className="col">{currentUser.profile.job_title}</div>
                    </div>
                    <div className="form-group dotted" />
                    <div className="row">
                      <div className="col">Industry</div>
                      <div className="col">{currentUser.profile.industry}</div>
                    </div>
                    <div className="row">
                      <div className="col">Job Function</div>
                      <div className="col">
                        {currentUser.profile.job_function}
                      </div>
                    </div>
                    <div className="row">
                      <div className="col">Years of Work Experience</div>
                      <div className="col">
                        {
                          fromPairs(EMPLOYMENT_EXPERIENCE)[
                            currentUser.profile.years_experience
                          ]
                        }
                      </div>
                    </div>
                    <div className="row">
                      <div className="col">Company Size</div>
                      <div className="col">
                        {
                          fromPairs(EMPLOYMENT_SIZE)[
                            currentUser.profile.company_size
                          ]
                        }
                      </div>
                    </div>
                    <div className="row">
                      <div className="col">Leadership Level</div>
                      <div className="col">
                        {currentUser.profile.leadership_level}
                      </div>
                    </div>
                    <div className="row">
                      <div className="col">Highest Level of Education</div>
                      <div className="col">
                        {currentUser.profile.highest_education}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="col-12 auth-form">
                    <div className="row">
                      You must be logged in to view your profile.
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </DocumentTitle>
    )
  }
}

const mapStateToProps = createStructuredSelector({
  currentUser: currentUserSelector,
  countries:   queries.users.countriesSelector
})

const mapPropsToConfigs = () => [
  queries.users.currentUserQuery(),
  queries.users.countriesQuery()
]

export default compose(
  connect(mapStateToProps),
  connectRequest(mapPropsToConfigs)
)(ViewProfilePage)
