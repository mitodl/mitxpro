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
        .at(1)
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
          .at(index + 2)
          .text(),
        `${topic.name} (${topic.course_count})`,
      );
      assert.equal(
        wrapper
          .find("a")
          .at(index + 2)
          .prop("href"),
        `/catalog/?topic=${topic.name}`,
      );
    });
  });

  it("has a link to the catalog page with programs tab active", () => {
    assert.equal(
      shallow(<CatalogMenu courseTopics={courseTopics} />)
        .find("a")
        .at(5)
        .prop("href"),
      "/catalog/?active-tab=programs-tab",
    );
  });

  describe("when isMobile is true", () => {
    it("renders mobile-drawer-section instead of dropdown", () => {
      const wrapper = shallow(
        <CatalogMenu courseTopics={courseTopics} isMobile={true} />,
      );

      assert.isTrue(wrapper.find(".mobile-drawer-section").exists());
      assert.isFalse(wrapper.find(".catalog-menu.dropdown").exists());
    });

    it("renders course topics with mobile-specific classes", () => {
      const wrapper = shallow(
        <CatalogMenu courseTopics={courseTopics} isMobile={true} />,
      );

      const allTopicsLink = wrapper.find(".mobile-catalog-item.all-topics");
      assert.isTrue(allTopicsLink.exists());
      assert.equal(allTopicsLink.text(), "All Topics");

      const topicLinks = wrapper
        .find(".mobile-catalog-item")
        .not(".all-topics");
      assert.equal(topicLinks.length, courseTopics.length);
    });

    it("does not render dropdown elements when in mobile mode", () => {
      const wrapper = shallow(
        <CatalogMenu courseTopics={courseTopics} isMobile={true} />,
      );

      assert.isFalse(wrapper.find(".dropdown-toggle").exists());
      assert.isFalse(wrapper.find(".dropdown-menu").exists());
      assert.isFalse(wrapper.find(".dropdown-divider").exists());
    });
  });
});
