// @flow
/* global SETTINGS: false */
import React, { useState, useEffect } from "react";

import { routes } from "../lib/urls";
import UserMenu from "./UserMenu";
import CatalogMenu from "./CatalogMenu";
import AuthButtons from "./input/AuthButtons";
import type { Location } from "react-router";

import type { CurrentUser } from "../flow/authTypes";
import type { CourseTopic } from "../flow/courseTypes";

type Props = {
  currentUser: ?CurrentUser,
  location: ?Location,
  errorPageHeader: ?boolean,
  courseTopics: Array<CourseTopic>,
};

const EXCLUDED_LOGIN_PATHS = [
  routes.ecommerceBulk.bulkPurchase,
  routes.ecommerceBulk.receipt,
];

const shouldShowLoginSignup = (location) =>
  !location || !EXCLUDED_LOGIN_PATHS.includes(location.pathname);

const TopAppBar = ({
  currentUser,
  location,
  errorPageHeader,
  courseTopics,
}: Props) => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const toggleDrawer = () => {
    setDrawerOpen((prev) => !prev);
  };

  useEffect(() => {
    document.body.style.overflow = drawerOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [drawerOpen]);

  const isAuthenticated = currentUser?.is_authenticated;
  const showLoginSignup = shouldShowLoginSignup(location);

  const renderMobileControls = () => (
    <div className="d-flex align-items-center d-md-none">
      <button
        className="navbar-toggler nav-opener d-flex align-items-center"
        type="button"
        onClick={toggleDrawer}
        aria-controls="nav"
        aria-expanded={drawerOpen}
        aria-label="Toggle navigation"
      >
        <span className="navbar-toggler-icon" />
        Menu
      </button>

      {showLoginSignup && isAuthenticated && (
        <div className="mobile-user-menu">
          <UserMenu currentUser={currentUser} />
        </div>
      )}
    </div>
  );

  const renderDesktopNav = () => (
    <ul
      id="nav"
      className="navbar-collapse d-none d-md-flex px-0 justify-content-end"
    >
      <li>
        <CatalogMenu courseTopics={courseTopics} />
      </li>
      {SETTINGS.enable_enterprise && (
        <li>
          <a
            href={routes.enterprise}
            className="enterprise-link"
            aria-label="enterprise"
          >
            Enterprise
          </a>
        </li>
      )}
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
      {showLoginSignup &&
        (currentUser && currentUser.is_authenticated ? (
          <li>
            <UserMenu currentUser={currentUser} />
          </li>
        ) : (
          <AuthButtons />
        ))}
    </ul>
  );

  const renderMobileDrawer = () => (
    <div className={`mobile-drawer d-md-none ${drawerOpen ? "open" : ""}`}>
      <div className="drawer-header">
        <button
          onClick={toggleDrawer}
          className="close-drawer"
          aria-label="Close menu"
        >
          &times;
        </button>
      </div>

      {showLoginSignup && !isAuthenticated && (
        <AuthButtons isMobile onClick={() => drawerOpen && toggleDrawer()} />
      )}

      <div className="mobile-drawer-section">
        <CatalogMenu courseTopics={courseTopics} isMobile={true} />
      </div>

      <div className="mobile-drawer-section">
        <a
          className="mobile-drawer-heading"
          href="/catalog/?active-tab=programs-tab"
          aria-label="Programs"
        >
          Programs
        </a>
        <a href={routes.webinars} className="mobile-drawer-heading">
          Webinars
        </a>
        <a href={routes.blog} className="mobile-drawer-heading">
          Blog
        </a>
        {SETTINGS.enable_enterprise && (
          <a href={routes.enterprise} className="mobile-drawer-heading">
            Enterprise
          </a>
        )}
      </div>
    </div>
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
          {!errorPageHeader && (
            <>
              {renderMobileControls()}
              {renderDesktopNav()}
              {renderMobileDrawer()}
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
