// @flow
/* global SETTINGS:false */
import React from "react"
import MixedLink from "./MixedLink"
import { routes } from "../lib/urls"

import type { User } from "../flow/authTypes"

type Props = {
  /* This is here for future use when we have custom profile avatars */
  currentUser: User
}

const UserMenu = ({ currentUser }: Props) => {
  return (
    <div className="user-menu dropdown">
      <div
        className="col-2 dropdown-toggle"
        id="dropdownMenuButton"
        data-toggle="dropdown"
        aria-haspopup="true"
        aria-expanded="false"
      >
        <img
          /* Use default profile avatar for now */
          src="/static/images/avatar_default.png"
          alt={`Profile image for ${currentUser.name}`}
          className={`profile-image`}
        />
      </div>
      <div className="dropdown-menu" aria-labelledby="dropdownMenuButton">
        <div className="dropdown-item">
          <div className="dropdown-icon icon-21 icon-profile" />
          <MixedLink dest={routes.profile.view} aria-label="Profile">
            Profile
          </MixedLink>
        </div>
        <div className="dropdown-item">
          <div className="dropdown-icon icon-dashboard" />
          <MixedLink dest={routes.dashboard} aria-label="Dashboard">
            Dashboard
          </MixedLink>
        </div>
        <div className="dropdown-divider" />
        <div className="dropdown-item">
          <div className="dropdown-icon icon-logout" />
          <MixedLink dest={routes.logout} aria-label="Sign Out">
            Sign Out
          </MixedLink>
        </div>
      </div>
    </div>
  )
}

export default UserMenu
