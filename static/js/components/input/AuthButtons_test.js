// @flow
import React from "react";

import { assert } from "chai";
import { shallow } from "enzyme";

import AuthButtons from "./AuthButtons";

import { routes } from "../../lib/urls";

describe("AuthButtons component", () => {
  it("has a link to login", () => {
    assert.equal(
      shallow(<AuthButtons isMobile={false} />)
        .find("MixedLink")
        .at(0)
        .prop("dest"),
      routes.login.begin,
    );
  });

  it("has a link to register", () => {
    assert.equal(
      shallow(<AuthButtons isMobile={false} />)
        .find("MixedLink")
        .at(1)
        .prop("dest"),
      routes.register.begin,
    );
  });
});
