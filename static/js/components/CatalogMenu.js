// @flow
/* global SETTINGS:false */
import React from "react";

import type { CourseTopic } from "../flow/courseTypes";

type Props = {
  courseTopics: Array<CourseTopic>,
  isMobile?: boolean,
};

const CatalogMenu = ({ courseTopics, isMobile = false }: Props) => {
  if (isMobile) {
    return (
      <div className="mobile-drawer-section">
        <a
          className="mobile-drawer-heading"
          href="/catalog/"
          aria-label="Courses"
        >
          Courses
        </a>
        <div className="mobile-catalog-menu">
          <a
            className="mobile-catalog-item all-topics"
            href="/catalog/"
            aria-label="All Topics"
          >
            All Topics
          </a>
          {courseTopics
            ? courseTopics.map((courseTopic, index) => (
                <a
                  className="mobile-catalog-item"
                  key={index}
                  href={`/catalog/?topic=${encodeURIComponent(courseTopic.name)}`}
                  aria-label={courseTopic.name}
                >
                  {courseTopic.name} ({courseTopic.course_count || 0})
                </a>
              ))
            : null}
        </div>
      </div>
    );
  }

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
