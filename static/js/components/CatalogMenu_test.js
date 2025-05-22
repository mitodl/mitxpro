// @flow
import React from "react";
import { assert } from "chai";
import { mount, shallow } from "enzyme";

import CatalogMenu from "./CatalogMenu";
import { routes } from "../lib/urls";
import { makeCourseTopics } from "../factories/course";

describe("CatalogMenu component", () => {
  const courseTopics = makeCourseTopics();

  it("has a link to all courses tab", () => {
    assert.equal(
      shallow(<CatalogMenu courseTopics={courseTopics} />)
        .find("a")
        .at(0)
        .prop("href"),
      routes.catalog,
    );
  });

  it("has links to the course topic filters and link text is in required format", () => {
    const wrapper = shallow(<CatalogMenu courseTopics={courseTopics} />);
    // eslint-disable-next-line camelcase
    courseTopics.map((topic, index) => {
      assert.equal(
        wrapper
          .find("a")
          .at(index + 1)
          .text(),
        `${topic.name} (${topic.course_count})`,
      );
      assert.equal(
        wrapper
          .find("a")
          .at(index + 1)
          .prop("href"),
        `/catalog/?topic=${topic.name}`,
      );
    });
  });

  it("has a link to the catalog page with programs tab active", () => {
    assert.equal(
      shallow(<CatalogMenu courseTopics={courseTopics} />)
        .find("a")
        .at(4)
        .prop("href"),
      "/catalog/?active-tab=programs-tab",
    );
  });

  [
    { key: "Enter", label: "Enter" },
    { key: " ", label: "Space" },
  ].map(({ key, label }) =>
    it(`toggles dropdown using ${label} key`, () => {
      const wrapper = mount(<CatalogMenu courseTopics={courseTopics} />);
      const toggle = wrapper.find('[role="button"]');
      const getMenu = () => wrapper.find(".dropdown-menu");

      // Initially closed
      assert.isFalse(
        getMenu().hasClass("show"),
        "Dropdown should be initially closed",
      );

      // Open dropdown
      toggle.simulate("keydown", { key });
      wrapper.update();
      assert.isTrue(
        getMenu().hasClass("show"),
        `Dropdown should open on ${label}`,
      );

      // Close dropdown
      toggle.simulate("keydown", { key });
      wrapper.update();
      assert.isFalse(
        getMenu().hasClass("show"),
        `Dropdown should close on ${label}`,
      );
    }),
  );

  it("closes dropdown when clicking outside", () => {
    const wrapper = mount(<CatalogMenu courseTopics={courseTopics} />);
    const toggle = wrapper.find('[role="button"]');
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
