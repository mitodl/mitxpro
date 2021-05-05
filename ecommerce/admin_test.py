"""tests for admin classes"""
import pytest

from courses.factories import CourseFactory
from ecommerce.admin import OrderAdmin, DataConsentAgreementForm
from ecommerce.factories import OrderFactory, DataConsentAgreementFactory
from ecommerce.models import OrderAudit
from users.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_save_and_log_model(mocker):
    """
    Tests that the save_model() function on OrderAdmin creates an OrderAudit entry
    """
    assert OrderAudit.objects.count() == 0
    order = OrderFactory.create()
    admin = OrderAdmin(model=order, admin_site=mocker.Mock())
    mock_request = mocker.Mock(user=UserFactory.create())
    admin.save_model(
        request=mock_request, obj=admin.model, form=mocker.Mock(), change=mocker.Mock()
    )
    assert OrderAudit.objects.count() == 1


def test_consent_agreement_clean_model_validation_error():
    """
    Tests that the DataConsentAgreementForm validates data and throws specified errors
    """
    consent_agreement = DataConsentAgreementFactory.create()
    consent_data = {
        "company": consent_agreement.company.id,
        "is_global": False,
        "courses": None,
        "content": "Content",
    }
    consent_agreement_form = DataConsentAgreementForm(
        instance=consent_agreement, data=consent_data
    )
    assert consent_agreement_form.is_valid() is False
    assert consent_agreement_form.errors is not None
    assert (
        consent_agreement_form.errors["__all__"][0]
        == "You must either check All Courses box or select courses for the agreement"
    )

    consent_data["is_global"] = True
    consent_agreement_form = DataConsentAgreementForm(
        instance=consent_agreement, data=consent_data
    )
    assert consent_agreement_form.is_valid() is True
    assert consent_agreement_form.errors == {}
    consent_agreement_form.save(commit=True)

    consent_agreement_2 = DataConsentAgreementFactory.create()
    consent_agreement_form = DataConsentAgreementForm(
        instance=consent_agreement_2, data=consent_data
    )
    assert consent_agreement_form.is_valid() is False
    assert consent_agreement_form.errors is not None
    assert (
        consent_agreement_form.errors["__all__"][0]
        == "You already have a global agreement for this company"
    )


def test_global_consent_agreement_clear_courses():
    """
    Tests that the DataConsentAgreementForm clears the associated courses when is_global is True
    """
    courses = CourseFactory.create()
    consent_agreement = DataConsentAgreementFactory.create(courses=[courses])
    consent_agreement_form = DataConsentAgreementForm(
        instance=consent_agreement,
        data={
            "company": consent_agreement.company.id,
            "is_global": True,
            "Courses": consent_agreement.courses,
            "content": "Some Content",
        },
    )
    assert consent_agreement_form.is_valid() is True
    consent_agreement_form.save(commit=True)
    assert consent_agreement_form.errors == {}
    consent_agreement.refresh_from_db()
    assert len(consent_agreement.courses.all()) == 0
