// @flow
/* global SETTINGS:false */
import React from "react";

import type { CourseTopic } from "../flow/courseTypes";

type Props = {
  courseTopics: Array<CourseTopic>,
};

const CatalogMenu = ({ courseTopics }: Props) => {
  return (
    <div className="catalog-menu dropdown">
      <div
        className="col-2 dropdown-toggle"
        id="dropdownMenuButton"
        data-toggle="dropdown"
        aria-haspopup="true"
        aria-expanded="false"
        aria-label="courses"
      >
        Courses
      </div>
      <div className="dropdown-menu" aria-labelledby="dropdownMenuButton">
        <a
          className="dropdown-item bold"
          href="/catalog/"
          aria-label="All Topics"
        >
          All Topics
        </a>
        {courseTopics
          ? courseTopics.map((courseTopic, index) => (
              <a
                className="dropdown-item"
                key={index}
                href={`/catalog/?topic=${encodeURIComponent(courseTopic.name)}`}
                aria-label={courseTopic.name}
              >
                {courseTopic.name} ({courseTopic.course_count})
              </a>
            ))
          : null}
        <div className="dropdown-divider" />
        <a
          className="dropdown-item bold"
          href="/catalog/?active-tab=programs-tab"
          aria-label="All Topics"
        >
          Programs
        </a>
      </div>
    </div>
  );
};

export default CatalogMenu;
