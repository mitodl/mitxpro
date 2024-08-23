// @flow
/* global SETTINGS:false */
import React from "react";

import MixedLink from "./MixedLink";
import { routes } from "../lib/urls";

import type { User } from "../flow/authTypes";

type Props = {
  /* This is here for future use when we have custom profile avatars */
  currentUser: User,
};

const UserMenu = ({ currentUser }: Props) => {
  return (
    <div className="user-menu dropdown">
      <a
        className="col-2 dropdown-toggle"
        id="dropdownMenuButton"
        data-toggle="dropdown"
        aria-haspopup="true"
        aria-expanded="false"
        href="#"
        role="button"
        data-bs-toggle="dropdown"
      >
        <img
          /* Use default profile avatar for now */
          src="/static/images/avatar_default.png"
          alt={`Profile image for ${currentUser.name}`}
          className={`profile-image`}
          width={34}
          height={34}
        />
      </a>
      <ul className="dropdown-menu" aria-labelledby="dropdownMenuButton">
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
          aria-label="settings"
        >
          <div className="dropdown-icon icon-21 icon-settings" />
          Settings
        </MixedLink>

        <div className="dropdown-divider" />
        <a className="dropdown-item" href={routes.logout} aria-label="Sign Out">
          <div className="dropdown-icon icon-logout" />
          Sign Out
        </a>
      </ul>
    </div>
  );
};

export default UserMenu;
