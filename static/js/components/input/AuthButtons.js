// @flow
import React from "react";

import { routes } from "../../lib/urls";
import MixedLink from "../MixedLink";

type Props = {
  isMobile?: boolean,
};

const AuthButtons = ({ isMobile = false }: Props) => {
  const authLinks = [
    {
      key: "login",
      label: "Sign In",
      dest: routes.login.begin,
      ariaLabel: "Login",
    },
    {
      key: "create-account",
      label: "Create Account",
      dest: routes.register.begin,
      ariaLabel: "Create Account",
    },
  ];

  const className = isMobile ? "mobile-auth-button" : "button";

  const buttons = authLinks.map(({ key, label, dest, ariaLabel }) => (
    <MixedLink
      key={key}
      dest={dest}
      className={className}
      aria-label={ariaLabel}
    >
      {label}
    </MixedLink>
  ));

  return isMobile ? (
    <div className="mobile-auth-buttons">{buttons}</div>
  ) : (
    <>
      {buttons.map((button) => (
        <li key={button.key}>{button}</li>
      ))}
    </>
  );
};

export default AuthButtons;
