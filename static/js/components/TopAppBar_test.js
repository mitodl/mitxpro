// @flow
/* global SETTINGS: false */
import React from "react";
import { assert } from "chai";
import { shallow } from "enzyme";

import TopAppBar from "./TopAppBar";

import { routes } from "../lib/urls";
import { makeUser, makeAnonymousUser } from "../factories/user";
import { makeCourseTopics } from "../factories/course";

describe("TopAppBar component", () => {
  describe("for anonymous users", () => {
    const user = makeAnonymousUser();

    it("has a link to login and register", () => {
      const wrapper = shallow(
        <TopAppBar
          currentUser={null}
          location={null}
          errorPageHeader={null}
          courseTopics={[]}
        />,
      );

      assert.isTrue(wrapper.find("AuthButtons").exists());
    });

    it("has a button to collapse the menu", () => {
      assert.isOk(
        shallow(
          <TopAppBar
            currentUser={user}
            location={null}
            errorPageHeader={null}
            courseTopics={[]}
          />,
        )
          .find("button")
          .exists(),
      );
    });

    it("does not have a login/register on ecommerce bulk page", () => {
      const location = { pathname: "/ecommerce/bulk/", hash: "", search: "" };
      const wrapper = shallow(
        <TopAppBar
          currentUser={user}
          location={location}
          errorPageHeader={null}
          courseTopics={[]}
        />,
      );
      assert.isNotOk(wrapper.find("UserMenu").exists());
      assert.isNotOk(wrapper.find("MixedLink").exists());
    });

    it("does not have a login/register on ecommerce bulk receipt page", () => {
      const location = {
        pathname: "/ecommerce/bulk/receipt/",
        hash: "",
        search: "",
      };
      const wrapper = shallow(
        <TopAppBar
          currentUser={user}
          location={location}
          errorPageHeader={null}
          courseTopics={[]}
        />,
      );
      assert.isNotOk(wrapper.find("UserMenu").exists());
      assert.isNotOk(wrapper.find("MixedLink").exists());
    });
  });
  describe("for logged in users", () => {
    const user = makeUser();
    const courseTopics = makeCourseTopics();

    it("has a UserMenu component", () => {
      assert.isOk(
        shallow(
          <TopAppBar
            currentUser={user}
            location={null}
            errorPageHeader={null}
            courseTopics={[]}
          />,
        )
          .find("UserMenu")
          .exists(),
      );
    });
    it("has a CatalogMenu component", () => {
      assert.isOk(
        shallow(
          <TopAppBar
            currentUser={user}
            location={null}
            errorPageHeader={null}
            courseTopics={courseTopics}
          />,
        )
          .find("CatalogMenu")
          .exists(),
      );
      assert.equal(
        shallow(
          <TopAppBar
            currentUser={user}
            location={null}
            errorPageHeader={null}
            courseTopics={courseTopics}
          />,
        )
          .find("a")
          .at(1)
          .prop("href"),
        routes.webinars,
      );
      assert.equal(
        shallow(
          <TopAppBar
            currentUser={user}
            location={null}
            errorPageHeader={null}
            courseTopics={courseTopics}
          />,
        )
          .find("a")
          .at(2)
          .prop("href"),
        routes.blog,
      );
    });

    it("does have a button to collapse the menu", () => {
      assert.isOk(
        shallow(
          <TopAppBar
            currentUser={user}
            location={null}
            errorPageHeader={null}
            courseTopics={[]}
          />,
        )
          .find("button")
          .exists(),
      );
    });

    it("does not have MixedLink's for login/registration", () => {
      assert.isNotOk(
        shallow(
          <TopAppBar
            currentUser={user}
            location={null}
            errorPageHeader={null}
            courseTopics={[]}
          />,
        )
          .find("MixedLink")
          .exists(),
      );
    });

    it("does not have a login/register on ecommerce bulk page", () => {
      const location = { pathname: "/ecommerce/bulk/", hash: "", search: "" };
      const wrapper = shallow(
        <TopAppBar
          currentUser={user}
          location={location}
          errorPageHeader={null}
          courseTopics={[]}
        />,
      );
      assert.isNotOk(wrapper.find("UserMenu").exists());
      assert.isNotOk(wrapper.find("MixedLink").exists());
    });

    it("does not have a login/register on ecommerce bulk receipt page", () => {
      const location = {
        pathname: "/ecommerce/bulk/receipt/",
        hash: "",
        search: "",
      };
      const wrapper = shallow(
        <TopAppBar
          currentUser={user}
          location={location}
          errorPageHeader={null}
          courseTopics={courseTopics}
        />,
      );
      assert.isNotOk(wrapper.find("UserMenu").exists());
      assert.isOk(wrapper.find("CatalogMenu").exists());
      assert.isNotOk(wrapper.find("MixedLink").exists());
    });

    it("passes isMobile prop to CatalogMenu in mobile drawer", () => {
      const wrapper = shallow(
        <TopAppBar
          currentUser={user}
          location={null}
          errorPageHeader={null}
          courseTopics={courseTopics}
        />,
      );

      const mobileCatalogMenu = wrapper
        .find(".mobile-drawer-section")
        .find("CatalogMenu");
      assert.isOk(mobileCatalogMenu.exists());
      assert.isTrue(mobileCatalogMenu.prop("isMobile"));
    });

    it("toggles mobile drawer when menu button is clicked", () => {
      const wrapper = shallow(
        <TopAppBar
          currentUser={user}
          location={null}
          errorPageHeader={null}
          courseTopics={courseTopics}
        />,
      );

      const initialDrawerOpen = wrapper.find(".mobile-drawer").hasClass("open");
      wrapper.find(".navbar-toggler").simulate("click");
      assert.notEqual(
        initialDrawerOpen,
        wrapper.find(".mobile-drawer").hasClass("open"),
      );
    });
  });
});
