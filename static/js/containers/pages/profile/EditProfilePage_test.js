// @flow
import { assert } from "chai";
import { map } from "ramda";
import sinon from "sinon";

import EditProfilePage, {
  EditProfilePage as InnerEditProfilePage,
} from "./EditProfilePage";
import {
  makeAnonymousUser,
  makeCountries,
  makeUser,
} from "../../../factories/user";
import IntegrationTestHelper from "../../../util/integration_test_helper";
import { ALERT_TYPE_TEXT } from "../../../constants";

describe("EditProfilePage", () => {
  let helper, renderPage;
  const user = makeUser();
  const countries = makeCountries();

  beforeEach(() => {
    helper = new IntegrationTestHelper();

    renderPage = helper.configureHOCRenderer(
      EditProfilePage,
      InnerEditProfilePage,
      {
        entities: {
          currentUser: user,
          countries: countries,
        },
      },
      {},
    );
  });

  afterEach(() => {
    helper.cleanup();
  });

  it("renders the page for a logged in user", async () => {
    const { inner } = await renderPage();
    assert.isTrue(inner.find("EditProfileForm").exists());
  });

  it("renders the page for an anonymous user", async () => {
    const { inner } = await renderPage({
      entities: {
        currentUser: makeAnonymousUser(),
        countries: countries,
      },
    });
    assert.isFalse(inner.find("EditProfileForm").exists());
    assert.isTrue(
      inner
        .find(".auth-page")
        .text()
        .includes("You must be logged in to edit your profile."),
    );
  });

  //
  [
    [true, true],
    [true, false],
    [false, true],
    [false, false],
  ].forEach(([hasError, hasEmptyFields]) => {
    it(`submits the updated profile ${
      hasEmptyFields ? "with some empty fields " : ""
    }${hasError ? "and received an error" : "successfully"}`, async () => {
      // $FlowFixMe
      user.profile.company_size = hasEmptyFields ? "" : 50;
      // $FlowFixMe
      user.profile.years_experience = hasEmptyFields ? "" : 5;
      // $FlowFixMe
      user.profile.highest_education = hasEmptyFields ? "" : "Doctorate";

      const { inner } = await renderPage();
      const setSubmitting = helper.sandbox.stub();
      const setErrors = helper.sandbox.stub();
      const values = user;
      const actions = {
        setErrors,
        setSubmitting,
      };

      helper.handleRequestStub.returns({
        status: hasError ? 400 : 200,
        body: {
          errors: hasError ? "some errors" : null,
        },
      });

      await inner.find("EditProfileForm").prop("onSubmit")(values, actions);

      const expectedPayload = {
        ...user,
        profile: {
          ...user.profile,
        },
      };
      if (hasEmptyFields) {
        // $FlowFixMe
        expectedPayload.profile.company_size = null;
        // $FlowFixMe
        expectedPayload.profile.years_experience = null;
        // $FlowFixMe
        expectedPayload.profile.highest_education = "";
      }

      sinon.assert.calledWith(
        helper.handleRequestStub,
        "/api/users/me",
        "PATCH",
        {
          body: expectedPayload,
          credentials: undefined,
          headers: { "X-CSRFTOKEN": null },
        },
      );
      sinon.assert.calledWith(setSubmitting, false);
      if (hasError) {
        assert.equal(setErrors.length, 0);
        assert.isNull(helper.currentLocation);
      } else {
        assert.equal(helper.currentLocation.location.pathname, "/profile/");
      }
    });
  });

  //
  [
    [
      "profile",
      { profile: { birth_year: "Birth year must be between 1906 and 2013." } },
    ],
    [
      "address",
      {
        legal_address: {
          city: "Ensure this field has no more than 50 characters.",
        },
      },
    ],
    [
      "profile and address",
      {
        profile: { birth_year: "Birth year must be between 1906 and 2013." },
        legal_address: {
          city: "Ensure this field has no more than 50 characters.",
        },
      },
    ],
  ].forEach(([description, expectedErrors]) => {
    it(`shows ${description} field errors and stays on the page when the API rejects them`, async () => {
      const { inner } = await renderPage();
      const setSubmitting = helper.sandbox.stub();
      const setErrors = helper.sandbox.stub();

      // mitxpro.exceptions.exception_handler wraps serializer errors in "errors"
      helper.handleRequestStub.returns({
        status: 400,
        body: {
          errors: map(
            map((error) => [error]),
            expectedErrors,
          ),
        },
      });

      await inner.find("EditProfileForm").prop("onSubmit")(user, {
        setErrors,
        setSubmitting,
      });

      sinon.assert.calledWith(setErrors, expectedErrors);
      sinon.assert.calledWith(setSubmitting, false);
      assert.isNull(helper.currentLocation);
    });
  });

  it("shows a failure notification and stays on the page when the save fails without field errors", async () => {
    const { inner, store } = await renderPage();
    const setSubmitting = helper.sandbox.stub();
    const setErrors = helper.sandbox.stub();

    helper.handleRequestStub.returns({ status: 503 });

    await inner.find("EditProfileForm").prop("onSubmit")(user, {
      setErrors,
      setSubmitting,
    });

    assert.deepEqual(store.getState().ui.userNotifications, {
      "profile-update-failed-status": {
        type: ALERT_TYPE_TEXT,
        color: "danger",
        props: {
          text: "Unable to update your profile, please try again later.",
        },
      },
    });
    sinon.assert.notCalled(setErrors);
    sinon.assert.calledWith(setSubmitting, false);
    assert.isNull(helper.currentLocation);
  });
});
