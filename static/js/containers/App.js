// @flow
import React from "react"
import { Route } from "react-router"
import type { Match } from "react-router"

import CourseTitleHeader from "./CourseTitleHeader"
import CourseDashboardPage from "./CourseDashboardPage"
import CourseDetailPage from "./CourseDetailPage"

export default class App extends React.Component<*, void> {
  props: {
    match: Match
  }

  render() {
    return (
      <div className="app">
        <CourseTitleHeader />
        <Route exact path="/" component={CourseDashboardPage} />
        <Route exact path="/courses/:courseId" component={CourseDetailPage} />
      </div>
    )
  }
}
