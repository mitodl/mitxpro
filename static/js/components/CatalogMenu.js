// @flow
/* global SETTINGS:false */
import React from "react"

import MixedLink from "./MixedLink"
import { routes } from "../lib/urls"

import type { User } from "../flow/authTypes"
import type {CourseTopic} from "../flow/courseTypes"
import {Field} from "formik"
import {formatRunTitle} from "../lib/ecommerce"

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
        {
          courseTopics.map(courseTopic =>
            (
              <MixedLink className="dropdown-item" dest="/catalog/" aria-label={courseTopic.name}>{courseTopic.name} ({courseTopic.course_count})</MixedLink>
            )
          )
        }
      </div>
    </div>
  )
}

export default CatalogMenu
