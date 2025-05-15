// @flow
/* global SETTINGS: false */
import React, { useState } from "react";

import { routes } from "../lib/urls";
import MixedLink from "./MixedLink";
import UserMenu from "./UserMenu";
import CatalogMenu from "./CatalogMenu";
import type { Location } from "react-router";

import type { CurrentUser } from "../flow/authTypes";
import type { CourseTopic } from "../flow/courseTypes";

type Props = {
  currentUser: ?CurrentUser,
  location: ?Location,
  errorPageHeader: ?boolean,
  courseTopics: Array<CourseTopic>,
};

const shouldShowLoginSignup = (location) =>
  !location ||
  !(
    location.pathname === routes.ecommerceBulk.bulkPurchase ||
    location.pathname === routes.ecommerceBulk.receipt
  );

const TopAppBar = ({
  currentUser,
  location,
  errorPageHeader,
  courseTopics,
}: Props) => {
  const [drawerOpen, setDrawerOpen] = useState(false);

  const toggleDrawer = () => {
    setDrawerOpen(!drawerOpen);
    document.body.style.overflow = !drawerOpen ? "hidden" : "";
  };

  const navigationItems = (
    <>
      <li>
        <CatalogMenu courseTopics={courseTopics} />
      </li>
      {SETTINGS.enable_enterprise ? (
        <li>
          <a
            href={routes.enterprise}
            className="enterprise-link"
            aria-label="enterprise"
          >
            Enterprise
          </a>
        </li>
      ) : null}
      <li>
        <a
          href={routes.webinars}
          className="webinar-link"
          aria-label="webinars"
        >
          Webinars
        </a>
      </li>
      <li>
        <a href={routes.blog} className="blog-link" aria-label="blog">
          Blog
        </a>
      </li>
      {shouldShowLoginSignup(location) ? (
        currentUser && currentUser.is_authenticated ? (
          <li>
            <UserMenu currentUser={currentUser} />
          </li>
        ) : (
          <React.Fragment>
            <li>
              <MixedLink
                dest={routes.login.begin}
                className="button"
                aria-label="Login"
              >
                Sign In
              </MixedLink>
            </li>
            <li>
              <MixedLink
                dest={routes.register.begin}
                className="button"
                aria-label="Login"
              >
                Create Account
              </MixedLink>
            </li>
          </React.Fragment>
        )
      ) : null}
    </>
  );

  return (
    <header className="header-holder">
      <div className="container">
        <nav className="sub-nav navbar navbar-expand-md link-section">
          <a href={routes.root} className="xpro-link">
            <img
              src="/static/images/mit-xpro-logo.svg"
              className="site-logo"
              alt={SETTINGS.site_name}
            />
          </a>
          {errorPageHeader ? null : (
            <button
              className="navbar-toggler nav-opener"
              type="button"
              data-toggle="collapse"
              data-target="#nav"
              aria-controls="nav"
              aria-expanded="false"
              aria-label="Toggle navigation"
            >
              <span className="navbar-toggler-icon" />
              Menu
            </button>
          )}
          {errorPageHeader ? null : (
            <>
              <ul
                id="nav"
                className="navbar-collapse d-none d-md-flex px-0 justify-content-end"
              >
                {navigationItems}
              </ul>
              <div
                className={`mobile-drawer d-md-none ${drawerOpen ? "open" : ""}`}
              >
                <div className="drawer-header">
                  <button
                    onClick={toggleDrawer}
                    className="close-drawer"
                    aria-label="Close menu"
                  >
                    &times;
                  </button>
                </div>
                <ul className="drawer-nav">{navigationItems}</ul>
              </div>

              {drawerOpen && (
                <div
                  className="drawer-overlay d-md-none"
                  onClick={toggleDrawer}
                />
              )}
            </>
          )}
        </nav>
      </div>
    </header>
  );
};

export default TopAppBar;
