"""
Management command to repair missing courseware records
"""
from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from requests.exceptions import HTTPError

from courseware.api import create_user

User = get_user_model()


class Command(BaseCommand):
    """
    Management command to repair missing courseware records
    """

    help = "Repairs missing courseware records"

    def handle(self, *args, **options):
        """Walk all users who are missing records and repair them"""

        users_to_repair = User.objects.annotate(
            courseware_user_count=Count("courseware_users"),
            openedx_api_auth_count=Count("openedx_api_auth"),
        ).filter(Q(courseware_user_count=0) | Q(openedx_api_auth_count=0))

        self.stdout.write(
            self.style.SUCCESS(f"Repairing {users_to_repair.count()} users")
        )

        error_count = 0
        success_count = 0

        for user in users_to_repair.iterator():
            try:
                create_user(user)
            except HTTPError as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"{user.username} ({user.email}): Failed to repair: {exc.response.json()}"
                    )
                )
                error_count += 1
            except Exception as exc:  # pylint: disable=broad-except
                self.stderr.write(
                    self.style.ERROR(
                        f"{user.username} ({user.email}): Failed to repair: {str(exc)}"
                    )
                )
                error_count += 1
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"{user.username} ({user.email}): Success")
                )
                success_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Repair Complete: {success_count} repaired, {error_count} failures"
            )
        )
