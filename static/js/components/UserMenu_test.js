// @flow
import React from "react";
import { assert } from "chai";
import { mount, shallow } from "enzyme";
import sinon from "sinon";

import { MemoryRouter } from "react-router";
import UserMenu from "./UserMenu";
import { routes } from "../lib/urls";
import { makeUser } from "../factories/user";

describe("UserMenu component", () => {
  const user = makeUser();

  let consoleWarnStub;

  before(() => {
    const originalConsoleWarning = console.warn;
    consoleWarnStub = sinon.stub(console, "warn").callsFake((msg, ...args) => {
      if (
        typeof msg === "string" &&
        (msg.includes("componentWillMount has been renamed") ||
          msg.includes("componentWillReceiveProps has been renamed"))
      ) {
        return; // suppress these warnings
      }
      originalConsoleWarning.call(console, msg, ...args); // otherwise print normally
    });
  });

  after(() => {
    consoleWarnStub.restore();
  });

  it("has a link to profile", () => {
    assert.equal(
      shallow(<UserMenu currentUser={user} />)
        .find("MixedLink")
        .at(0)
        .prop("dest"),
      routes.profile.view,
    );
  });

  it("has a link to dashboard", () => {
    assert.equal(
      shallow(<UserMenu currentUser={user} />)
        .find("MixedLink")
        .at(1)
        .prop("dest"),
      routes.dashboard,
    );
  });

  it("has a link to logout", () => {
    assert.equal(
      shallow(<UserMenu currentUser={user} />)
        .find("a")
        .at(0)
        .prop("href"),
      routes.logout,
    );
  });

  [
    { key: "Enter", label: "Enter" },
    { key: " ", label: "Space" },
  ].forEach(({ key, label }) => {
    it(`toggles dropdown using ${label} key`, () => {
      const wrapper = mount(
        <MemoryRouter>
          <UserMenu currentUser={user} />
        </MemoryRouter>,
      );
      const toggle = wrapper.find('[aria-label="User menu"]');
      const getMenu = () => wrapper.find(".dropdown-menu");

      assert.isFalse(
        getMenu().hasClass("show"),
        "Dropdown should be initially closed",
      );

      toggle.simulate("keydown", { key });
      wrapper.update();
      assert.isTrue(
        getMenu().hasClass("show"),
        `Dropdown should open on ${label}`,
      );

      toggle.simulate("keydown", { key });
      wrapper.update();
      assert.isFalse(
        getMenu().hasClass("show"),
        `Dropdown should close on ${label}`,
      );
    });
  });

  it("closes dropdown when clicking outside", () => {
    const wrapper = mount(
      <MemoryRouter>
        <UserMenu currentUser={user} />
      </MemoryRouter>,
    );
    const toggle = wrapper.find('[aria-label="User menu"]');
    const getMenu = () => wrapper.find(".dropdown-menu");

    // Open the dropdown
    toggle.simulate("click");
    wrapper.update();
    assert.isTrue(
      getMenu().hasClass("show"),
      "Dropdown should be open after clicking toggle",
    );

    // Simulate click outside the component
    const clickEvent = new MouseEvent("mousedown", { bubbles: true });
    document.dispatchEvent(clickEvent);
    wrapper.update();

    assert.isFalse(
      getMenu().hasClass("show"),
      "Dropdown should be closed after clicking outside",
    );
  });
});
