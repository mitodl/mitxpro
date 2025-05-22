// @flow
/* global SETTINGS:false */
import React, { useState, useRef, useEffect } from "react";
import MixedLink from "./MixedLink";
import { routes } from "../lib/urls";

import type { User } from "../flow/authTypes";

type Props = {
  /* This is here for future use when we have custom profile avatars */
  currentUser: User,
};

const UserMenu = ({ currentUser }: Props) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<?HTMLDivElement>(null);

  const toggleDropdown = () => setIsOpen((prev) => !prev);

  const handleKeyDown = (e: SyntheticKeyboardEvent<>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggleDropdown();
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  const handleClickOutside = (e: MouseEvent) => {
    if (menuRef.current && !menuRef.current.contains(e.target)) {
      setIsOpen(false);
    }
  };

  useEffect(() => {
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  return (
    <div className="user-menu dropdown" ref={menuRef}>
      <div
        className="col-2 dropdown-toggle"
        id="dropdownMenuButton"
        aria-haspopup="true"
        aria-expanded={isOpen}
        aria-label="User menu"
        tabIndex="0"
        onClick={toggleDropdown}
        onKeyDown={handleKeyDown}
      >
        <img
          /* Use default profile avatar for now */
          src="/static/images/avatar_default.png"
          alt={`Profile image for ${currentUser.name}`}
          className="profile-image"
          width={34}
          height={34}
        />
      </div>
      <div
        className={`dropdown-menu ${isOpen ? "show" : ""}`}
        aria-labelledby="dropdownMenuButton"
      >
        <MixedLink
          className="dropdown-item"
          dest={routes.profile.view}
          aria-label="Profile"
        >
          <div className="dropdown-icon icon-21 icon-profile" />
          Profile
        </MixedLink>
        <MixedLink
          className="dropdown-item"
          dest={routes.dashboard}
          aria-label="Dashboard"
        >
          <div className="dropdown-icon icon-dashboard" />
          Dashboard
        </MixedLink>
        <MixedLink
          className="dropdown-item"
          dest={routes.accountSettings}
          aria-label="Settings"
        >
          <div className="dropdown-icon icon-21 icon-settings" />
          Settings
        </MixedLink>
        <div className="dropdown-divider" />
        <a className="dropdown-item" href={routes.logout} aria-label="Sign Out">
          <div className="dropdown-icon icon-logout" />
          Sign Out
        </a>
      </div>
    </div>
  );
};

export default UserMenu;
