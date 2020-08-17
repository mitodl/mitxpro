"""Tests for mitxpro models"""
from random import sample, randint, choice
from types import SimpleNamespace

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
import pytest

from mitxpro.models import PrefetchGenericQuerySet

pytestmark = pytest.mark.django_db

# pylint: disable=redefined-outer-name


@pytest.fixture(scope="module")
@pytest.mark.usefixtures("django_db_setup")
def test_models(django_db_blocker):
    """Fixture that creates test-only models"""
    with django_db_blocker.unblock():

        class SecondLevel1(models.Model):
            """Test-only model"""

        class SecondLevel2(models.Model):
            """Test-only model"""

        class FirstLevel1(models.Model):
            """Test-only model"""

            second_level = models.ForeignKey(SecondLevel1, on_delete=models.CASCADE)

        class FirstLevel2(models.Model):
            """Test-only model"""

            second_levels = models.ManyToManyField(SecondLevel2)

        class TestModelQuerySet(PrefetchGenericQuerySet):
            """Test-only QuerySet"""

        class Root(models.Model):
            """Test-only model"""

            objects = TestModelQuerySet.as_manager()

            content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey("content_type", "object_id")

        # we create our models "on the fly" in our test db
        with connection.schema_editor() as editor:
            editor.create_model(SecondLevel1)
            editor.create_model(SecondLevel2)
            editor.create_model(FirstLevel1)
            editor.create_model(FirstLevel2)
            editor.create_model(Root)

    yield SimpleNamespace(
        SecondLevel1=SecondLevel1,
        SecondLevel2=SecondLevel2,
        FirstLevel1=FirstLevel1,
        FirstLevel2=FirstLevel2,
        Root=Root,
    )


def test_prefetch_generic_related(django_assert_num_queries, test_models):
    """Test prefetch over a many-to-one relation"""
    second_levels1 = [test_models.SecondLevel1.objects.create() for _ in range(5)]
    first_levels1 = [
        test_models.FirstLevel1.objects.create(second_level=choice(second_levels1))
        for _ in range(10)
    ]

    second_levels2 = [test_models.SecondLevel2.objects.create() for _ in range(5)]
    first_levels2 = []
    for _ in range(10):
        first_level = test_models.FirstLevel2.objects.create()
        first_level.second_levels.set(sample(second_levels2, randint(1, 3)))
        first_levels2.append(first_level)

    roots = [
        test_models.Root.objects.create(content_object=choice(first_levels1))
        for _ in range(5)
    ] + [
        test_models.Root.objects.create(content_object=choice(first_levels2))
        for _ in range(5)
    ]

    with django_assert_num_queries(0):
        # verify the prefetch is lazy
        query = test_models.Root.objects.prefetch_related(
            "content_type"  # need this to avoid N+1 on this relation
        ).prefetch_generic_related(
            "content_type",
            {
                test_models.FirstLevel1: ["content_object__second_level"],
                test_models.FirstLevel2: ["content_object__second_levels"],
            },
        )

    # 1 query each for Root, ContentType, FirstLevel1, FirstLevel2, FirstLevel1, and SecondLevel2
    with django_assert_num_queries(6):
        assert len(query) == len(roots)
        for item in query:
            if isinstance(item.content_object, test_models.FirstLevel1):
                assert item.content_object.second_level is not None
            else:
                # .all() shouldn't cause a reevaulation
                assert len(item.content_object.second_levels.all()) > 0
