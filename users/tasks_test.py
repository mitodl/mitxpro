"""Users tasks tests"""
import pytest

from users.tasks import make_hubspot_contact_update


hubspot_property_mapping = {
    "name": ("user", "name"),
    "company": ("profile", "company"),
    "jobtitle": ("profile", "job_title"),
    "gender": ("profile", "gender"),
}


@pytest.mark.django_db
def test_make_hubspot_contact_update(user):
    """Test that make_hubspot_update creates an appropriate update out of the user"""
    update = make_hubspot_contact_update(user)
    assert update['email'] == user.email
    for prop in update['properties']:
        obj, key = hubspot_property_mapping[prop['property']]
        if obj == 'user':
            assert getattr(user, key) == prop['value']
        elif obj == 'profile':
            assert getattr(user.profile, key) == prop['value']
