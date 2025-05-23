// @flow
/* global SETTINGS:false */
import React from "react";

import type { CourseTopic } from "../flow/courseTypes";

type Props = {
  courseTopics: Array<CourseTopic>,
  isMobile?: boolean,
};

const CatalogMenu = ({ courseTopics, isMobile = false }: Props) => {
  const renderMenuItems = () => (
    <>
      <a
        className={
          isMobile ? "mobile-catalog-item all-topics" : "dropdown-item bold"
        }
        href="/catalog/"
        aria-label="All Topics"
      >
        All Topics
      </a>
      {courseTopics?.map((courseTopic, index) => (
        <a
          className={isMobile ? "mobile-catalog-item" : "dropdown-item"}
          key={index}
          href={`/catalog/?topic=${encodeURIComponent(courseTopic.name)}`}
          aria-label={courseTopic.name}
        >
          {courseTopic.name} ({courseTopic.course_count || 0})
        </a>
      ))}
    </>
  );

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
        <div className="mobile-catalog-menu">{renderMenuItems()}</div>
      </div>
    );
  }

  return (
    <div className="catalog-menu dropdown">
      <a
        className="col-2 dropdown-toggle"
        id="dropdownMenuButton"
        data-toggle="dropdown"
        aria-haspopup="true"
        aria-expanded="false"
        aria-label="courses"
        href="#"
        role="button"
        data-bs-toggle="dropdown"
        onKeyDown={(e) => {
          if (e.key === " ") {
            e.preventDefault();
            e.target.click();
          }
        }}
      >
        Courses
      </a>
      <ul className="dropdown-menu" aria-labelledby="dropdownMenuButton">
        {renderMenuItems()}
        <div className="dropdown-divider" />
        <a
          className="dropdown-item bold"
          href="/catalog/?active-tab=programs-tab"
          aria-label="Programs"
        >
          Programs
        </a>
      </ul>
    </div>
  );
};

export default CatalogMenu;
