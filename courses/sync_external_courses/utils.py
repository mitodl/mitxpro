from dataclasses import dataclass
from typing import Optional


@dataclass
class CoursewareInfo:
    """
    Data class for course information with named fields
    """

    code: str
    title: Optional[str] = None
    msg: Optional[str] = None


class StatItemsCollection:
    """Represents a category of statistics with its display information"""

    def __init__(self, key, label, display_name=None):
        """
        Initialize a stat category

        Args:
            key: The dictionary key for this stat
            display_name: Human-readable category name
            label: Description of the items
        """
        self.key = key
        self.label = label
        self.display_name = display_name or self._generate_display_name(key)
        self.items = []

    def _generate_display_name(self, key):
        """Generate a display name from the key"""
        return " ".join(word.capitalize() for word in key.split("_"))

    def add(self, code, title=None, msg=None):
        """Add an item to this stat category"""
        self.items.append(CoursewareInfo(code=code, title=title, msg=msg))

    def get_codes(self):
        """Get the set of unique codes in this category"""
        return {item.code for item in self.items if item.code is not None}

    def __len__(self):
        """Return the number of items in this category"""
        return len(self.items)


class StatsCollector:
    """Collector for external course sync statistics with named properties"""

    def __init__(self):
        self.categories = {
            "courses_created": StatItemsCollection(
                "courses_created", "External Course Codes"
            ),
            "existing_courses": StatItemsCollection(
                "existing_courses",
                "External Course Codes",
            ),
            "course_runs_created": StatItemsCollection(
                "course_runs_created",
                "External Course Run Codes",
            ),
            "course_runs_updated": StatItemsCollection(
                "course_runs_updated",
                "External Course Run Codes",
            ),
            "course_runs_without_prices": StatItemsCollection(
                "course_runs_without_prices",
                "External Course Run Codes",
            ),
            "course_runs_skipped": StatItemsCollection(
                "course_runs_skipped",
                "External Course Run Codes",
                display_name="Course Runs Skipped due to bad data",
            ),
            "course_runs_expired": StatItemsCollection(
                "course_runs_expired",
                "External Course Run Codes",
                display_name="Expired Course Runs",
            ),
            "course_runs_deactivated": StatItemsCollection(
                "course_runs_deactivated",
                "External Course Run Codes",
            ),
            "course_pages_created": StatItemsCollection(
                "course_pages_created",
                "External Course Codes",
            ),
            "course_pages_updated": StatItemsCollection(
                "course_pages_updated",
                "External Course Codes",
            ),
            "products_created": StatItemsCollection(
                "products_created",
                "Course Run courseware_ids",
            ),
            "product_versions_created": StatItemsCollection(
                "product_versions_created",
                "Course Run courseware_ids",
            ),
            "certificates_created": StatItemsCollection(
                "certificates_created",
                "Course Readable IDs",
                display_name="Certificate Pages Created",
            ),
            "certificates_updated": StatItemsCollection(
                "certificates_updated",
                "Course Readable IDs",
                display_name="Certificate Pages Updated",
            ),
        }

    def add_stat(self, key, code, title=None, msg=None):
        """
        Add an item to a specific stat category
        """
        if key in self.categories:
            existing_item = [
                item for item in self.categories[key].items if item.code == code
            ]
            if not existing_item:
                self.categories[key].add(code, title, msg)

    def add_bulk(self, key, codes):
        """
        Add multiple items within the same category
        """
        if key in self.categories:
            for code in codes:
                self.add_stat(key, code)

    def remove_duplicates(self, source_key, items_to_remove_key):
        """
        Remove items from one category that exist in another category
        """
        if (
            source_key not in self.categories
            or items_to_remove_key not in self.categories
        ):
            return

        codes_to_remove = {
            item.code for item in self.categories[items_to_remove_key].items
        }

        self.categories[source_key].items = [
            item
            for item in self.categories[source_key].items
            if item.code not in codes_to_remove
        ]

    def log_stats(self, logger):
        """
        Log all collected statistics
        """
        for category in self.categories.values():
            codes = category.get_codes()
            logger.log_style_success(
                f"Number of {category.display_name}: {len(codes)}."
            )
            logger.log_style_success(f"{category.label}: {codes or 0}\n")

    def email_stats(self):
        """
        Return statistics formatted for email template"
        """
        return {key: category.items for key, category in self.categories.items()}
