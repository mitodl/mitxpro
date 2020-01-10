"""
Management command to repair missing courseware records
"""
from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from requests.exceptions import HTTPError

from courseware.api import repair_faulty_edx_user
from mitxpro.utils import get_error_response_summary

User = get_user_model()


class Command(BaseCommand):
    """
    Management command to repair missing courseware records
    """

    help = "Repairs missing courseware records"

    def handle(self, *args, **options):
        """Walk all users who are missing records and repair them"""

        users_to_repair = User.faulty_courseware_users
        self.stdout.write(f"Repairing {users_to_repair.count()} users")

        error_count = 0
        success_count = 0

        for user in users_to_repair.iterator():
            result = []
            try:
                created_user, created_auth_token = repair_faulty_edx_user(user)
            except HTTPError as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"{user.username} ({user.email}): "
                        f"Failed to repair ({get_error_response_summary(exc.response)})"
                    )
                )
                error_count += 1
            except Exception as exc:  # pylint: disable=broad-except
                self.stderr.write(
                    self.style.ERROR(
                        f"{user.username} ({user.email}): Failed to repair (Exception: {str(exc)})"
                    )
                )
                error_count += 1
            else:
                if created_user:
                    result.append("Created edX user")
                if created_auth_token:
                    result.append("Created edX auth token")
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{user.username} ({user.email}): {', '.join(result)}"
                    )
                )
                success_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Repair Complete: {success_count} repaired, {error_count} failures"
            )
        )
