"""Test for user views"""
from datetime import timedelta
import pytest

from django.urls import reverse
from factory import fuzzy
from rest_framework import status
from social_django.models import UserSocialAuth

from mitxpro.test_utils import drf_datetime
from mitxpro.utils import now_in_utc
from users.api import User
from users.factories import UserFactory
from users.models import ChangeEmailRequest


@pytest.mark.django_db
def test_cannot_create_user(client):
    """Verify the api to create a user is nonexistent"""
    resp = client.post("/api/users/", data={"name": "Name"})

    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_cannot_update_user(user_client, user):
    """Verify the api to update a user is doesn't accept the verb"""
    resp = user_client.patch(
        reverse("users_api-detail", kwargs={"pk": user.id}), data={"name": "Name"}
    )

    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_get_user_by_id(user_client, user):
    """Test that user can request their own user by id"""
    resp = user_client.get(reverse("users_api-detail", kwargs={"pk": user.id}))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "created_on": drf_datetime(user.created_on),
        "updated_on": drf_datetime(user.updated_on),
    }


@pytest.mark.parametrize("is_anonymous", [True, False])
@pytest.mark.parametrize("show_enrollment_codes", [True, False])
def test_get_user_by_me(mocker, client, user, is_anonymous, show_enrollment_codes):
    """Test that user can request their own user by the 'me' alias"""
    if not is_anonymous:
        client.force_login(user)

    patched_unused_coupon_api = mocker.patch(
        "users.serializers.fetch_and_serialize_unused_coupons",
        return_value=[{"serialized": "data"}],
    )
    resp = client.get(reverse("users_api-me"))

    assert resp.status_code == status.HTTP_200_OK

    if is_anonymous:
        assert resp.json() == {
            "id": None,
            "username": "",
            "email": None,
            "legal_address": None,
            "is_anonymous": True,
            "is_authenticated": False,
            "profile": None,
            "unused_coupons": [],
        }
        patched_unused_coupon_api.assert_not_called()
    elif not is_anonymous and show_enrollment_codes:
        assert resp.json() == {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "legal_address": {
                "first_name": user.legal_address.first_name,
                "last_name": user.legal_address.last_name,
                "street_address": [user.legal_address.street_address_1],
                "city": user.legal_address.city,
                "state_or_territory": user.legal_address.state_or_territory,
                "country": user.legal_address.country,
                "postal_code": user.legal_address.postal_code,
            },
            "profile": {
                "gender": user.profile.gender,
                "company": user.profile.company,
                "company_size": user.profile.company_size,
                "job_title": user.profile.job_title,
                "birth_year": int(user.profile.birth_year),
                "leadership_level": user.profile.leadership_level,
                "job_function": user.profile.job_function,
                "years_experience": user.profile.years_experience,
                "highest_education": user.profile.highest_education,
                "industry": user.profile.industry,
            },
            "unused_coupons": patched_unused_coupon_api.return_value,
            "is_anonymous": False,
            "is_authenticated": True,
            "created_on": drf_datetime(user.created_on),
            "updated_on": drf_datetime(user.updated_on),
        }
        patched_unused_coupon_api.assert_called_with(user)
    elif not is_anonymous and not show_enrollment_codes:
        response = resp.json()
        patched_unused_coupon_api.assert_called_with(user)
        assert response["unused_coupons"] == patched_unused_coupon_api.return_value


@pytest.mark.django_db
def test_countries_states_view(client):
    """Test that a list of countries and states is returned"""
    resp = client.get(reverse("countries_api-list"))
    countries = {country["code"]: country for country in resp.json()}
    assert len(countries.get("US").get("states")) > 50
    assert {"code": "CA-QC", "name": "Quebec"} in countries.get("CA").get("states")
    assert len(countries.get("FR").get("states")) == 0
    assert countries.get("US").get("name") == "United States"
    assert countries.get("TW").get("name") == "Taiwan"


def test_create_email_change_request_invalid_password(user_drf_client, user):
    """Test that invalid password is returned"""
    resp = user_drf_client.post(
        "/api/change-emails/",
        data={
            "new_email": "abc@example.com",
            "password": user.password,
            "old_password": "abc",
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_create_email_change_request_existing_email(user_drf_client, user):
    """Test that create change email request gives validation error for existing user email"""
    new_user = UserFactory.create()
    user_password = user.password
    user.set_password(user.password)
    user.save()
    resp = user_drf_client.post(
        "/api/change-emails/",
        data={"new_email": new_user.email, "password": user_password},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_create_email_change_request_same_email(user_drf_client, user):
    """Test that user same email wouldn't be processed"""
    resp = user_drf_client.post(
        "/api/change-emails/",
        data={
            "new_email": user.email,
            "password": user.password,
            "old_password": user.password,
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_create_email_change_request_valid_email(user_drf_client, user, mocker):
    """Test that change request is created"""
    user_password = user.password
    user.set_password(user.password)
    user.save()

    mocker.patch("courseware.tasks.change_edx_user_email_async", return_value=None)
    mocker.patch("courseware.tasks.api.update_edx_user_email")
    mock_email = mocker.patch("mail.verification_api.send_verify_email_change_email")
    resp = user_drf_client.post(
        "/api/change-emails/",
        data={"new_email": "abc@example.com", "password": user_password},
    )

    assert resp.status_code == status.HTTP_201_CREATED

    code = mock_email.call_args[0][1].code
    assert code

    old_email = user.email
    resp = user_drf_client.patch(
        "/api/change-emails/{}/".format(code), data={"confirmed": True}
    )
    assert not UserSocialAuth.objects.filter(uid=old_email, user=user).exists()
    assert resp.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.email == "abc@example.com"


def test_create_email_change_request_expired_code(user_drf_client, user):
    """Check for expired code for Email Change Request"""
    change_request = ChangeEmailRequest.objects.create(
        user=user,
        new_email="abc@example.com",
        expires_on=now_in_utc() - timedelta(seconds=5),
    )

    resp = user_drf_client.patch(
        "/api/change-emails/{}/".format(change_request.code), data={"confirmed": True}
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_update_email_change_request_invalid_token(user_drf_client):
    """Test that invalid token doesn't work"""
    resp = user_drf_client.patch("/api/change-emails/abc/", data={"confirmed": True})
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_update_user_name_change(mocker, user_client, user, valid_address_dict):
    """Test that updating user's name is properly reflected in xPRO"""
    new_name = fuzzy.FuzzyText(prefix="Test-").fuzz()
    mocker.patch("courseware.api.update_edx_user_name")
    payload = {
        "name": new_name,
        "email": user.email,
        "legal_address": valid_address_dict,
    }

    resp = user_client.patch(
        reverse("users_api-me"), content_type="application/json", data=payload
    )

    assert resp.status_code == status.HTTP_200_OK
    # Checks that returned response has updated name
    assert resp.data["name"] == new_name
    # Checks that user's name in database is also updated
    assert User.objects.get(pk=user.pk).name == new_name


def test_update_user_name_change_edx(mocker, user_client, user, valid_address_dict):
    """Test that PATCH on user/me also calls update user's name api in edX if there is a name change in xPRO"""
    new_name = fuzzy.FuzzyText(prefix="Test-").fuzz()
    update_edx_mock = mocker.patch("courseware.api.update_edx_user_name")
    payload = {
        "name": new_name,
        "email": user.email,
        "legal_address": valid_address_dict,
    }
    resp = user_client.patch(
        reverse("users_api-me"), content_type="application/json", data=payload
    )

    assert resp.status_code == status.HTTP_200_OK
    # Checks that update edx user was called and only once when there was a change in user's name(Full Name)
    update_edx_mock.assert_called_once_with(user)


def test_update_user_no_name_change_edx(mocker, user_client, user, valid_address_dict):
    """Test that PATCH on user/me without name change doesn't call update user's name in edX"""
    update_edx_mock = mocker.patch("courseware.api.update_edx_user_name")
    resp = user_client.patch(
        reverse("users_api-me"),
        content_type="application/json",
        data={
            "name": user.name,
            "email": user.email,
            "legal_address": valid_address_dict,
        },
    )

    assert resp.status_code == status.HTTP_200_OK
    # Checks that update edx user was called not called when there is no change in user's name(Full Name)
    update_edx_mock.assert_not_called()
