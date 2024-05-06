// @flow
import React from "react";
import { assert } from "chai";
import { shallow } from "enzyme";

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
});
