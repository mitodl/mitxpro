// @flow
/* global SETTINGS:false */
import React from "react"

import type {CourseTopic} from "../flow/courseTypes"

type Props = {
  /* This is here for future use when we have custom profile avatars */
  courseTopics: Array<CourseTopic>
}

const CatalogMenu = ({ courseTopics }: Props) => {
  return (
    <div className="catalog-menu dropdown">
      <div
        className="col-2 dropdown-toggle"
        id="dropdownMenuButton"
        data-toggle="dropdown"
        aria-haspopup="true"
        aria-expanded="false"
      >
        Courses
      </div>
      <div className="dropdown-menu" aria-labelledby="dropdownMenuButton">
        <a className="dropdown-item bold" href="/catalog/" aria-label="All Topics">All Topics</a>
        {
          courseTopics.map(courseTopic =>
            (
              <a className="dropdown-item" href={`/catalog/?topic=${  courseTopic.name}`} aria-label={courseTopic.name}>{courseTopic.name} ({courseTopic.course_count})</a>
            )
          )
        }
        <div className="dropdown-divider" />
        <a className="dropdown-item bold" href="/catalog/" aria-label="All Topics">Programs</a>
      </div>
    </div>
  )
}

export default CatalogMenu
