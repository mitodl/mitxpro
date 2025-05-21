// @flow
/* global SETTINGS:false */
import React, { useState, useRef, useEffect } from "react";

import type { CourseTopic } from "../flow/courseTypes";

type Props = {
  courseTopics: Array<CourseTopic>,
};

const CatalogMenu = ({ courseTopics }: Props) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<?HTMLDivElement>(null);

  const toggleMenu = () => setIsOpen((open) => !open);

  const handleKeyDown = (e: SyntheticKeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggleMenu();
    }
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  return (
    <div className="catalog-menu dropdown" ref={menuRef}>
      <div
        className="col-2 dropdown-toggle"
        id="dropdownMenuButton"
        role="button"
        tabIndex={0}
        aria-haspopup="true"
        aria-expanded={isOpen}
        aria-label="Courses menu"
        onKeyDown={handleKeyDown}
        onClick={toggleMenu}
      >
        Courses
      </div>
      <div
        className={`dropdown-menu${isOpen ? " show" : ""}`}
        aria-labelledby="dropdownMenuButton"
      >
        <a
          className="dropdown-item bold"
          href="/catalog/"
          aria-label="All Topics"
        >
          All Topics
        </a>
        {courseTopics?.map((courseTopic, index) => (
          <a
            className="dropdown-item"
            key={index}
            href={`/catalog/?topic=${encodeURIComponent(courseTopic.name)}`}
            aria-label={courseTopic.name}
          >
            {courseTopic.name} ({courseTopic.course_count})
          </a>
        ))}
        <div className="dropdown-divider" />
        <a
          className="dropdown-item bold"
          href="/catalog/?active-tab=programs-tab"
          aria-label="Programs"
        >
          Programs
        </a>
      </div>
    </div>
  );
};

export default CatalogMenu;
