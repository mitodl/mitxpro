"""
Statistics collection and reporting for external course synchronization.

This module provides classes for collecting, organizing, and reporting
statistics about external course synchronization operations, with a focus
on named properties for better readability and maintenance.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CoursewareInfo:
    """
    Data class for courseware information with named fields
    """

    code: str
    title: Optional[str] = None
    msg: Optional[str] = None

    def __eq__(self, other):
        """
        Equality based solely on the code field.
        This allows sets to consider objects with the same code as equal.
        """
        if not isinstance(other, CoursewareInfo):
            return False
        return self.code == other.code

    def __hash__(self):
        """
        Hash based solely on the code field.
        This is needed for set operations and dictionary keys.
        """
        return hash(self.code)


class StatItemsCollection:
    """
    Manages a collection of statistical items within a specific category.

    This class serves as both a container for items in a statistics category
    and a metadata handler that provides display information about the category
    itself.
    """

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
        self.items = set()

    def _generate_display_name(self, key):
        """Generate a display name from the key"""
        return " ".join(word.capitalize() for word in key.split("_"))

    def add(self, code, title=None, msg=None):
        """Add an item to this stat category"""
        self.items.add(CoursewareInfo(code=code, title=title, msg=msg))

    def get_codes(self):
        """Get the set of unique codes in this stat category"""
        return {item.code for item in self.items if item.code is not None}

    def remove_items_with_codes(self, codes_to_remove):
        """
        Remove items with codes found in the provided set

        Args:
            codes_to_remove: Set of codes to exclude
        """
        self.items = {item for item in self.items if item.code not in codes_to_remove}

    def difference_update(self, other_collection):
        """
        Remove items whose codes exist in another collection

        Args:
            other_collection: Another StatItemsCollection to compare against
        """
        codes_to_remove = other_collection.get_codes()
        self.remove_items_with_codes(codes_to_remove)

    def __len__(self):
        """Return the number of items in this category"""
        return len(self.items)


class StatsCollector:
    """Collector for external course sync statistics with named properties"""

    def __init__(self):
        self.stats = {
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
        Add an item to a specific stat
        """
        if key in self.stats:
            self.stats[key].add(code, title, msg)

    def add_bulk(self, key, codes):
        """
        Add multiple items within the same stat
        """
        if key in self.stats:
            for code in codes:
                self.add_stat(key, code)

    def remove_duplicates(self, target_stat_key, reference_stat_key):
        """
        Filters out items from target stat category whose codes exist in reference stat category.
        """
        if target_stat_key not in self.stats or reference_stat_key not in self.stats:
            return

        self.stats[target_stat_key].difference_update(self.stats[reference_stat_key])

    def log_stats(self, log_func):
        """
        Log all collected statistics
        """
        log_func = log_func or self.logger.info

        for category in self.categories.values():
            codes = category.get_codes()
            log_func(f"Number of {category.display_name}: {len(codes)}.")
            log_func(f"{category.label}: {codes or 0}")

    def get_email_stats(self):
        """
        Return statistics formatted for email template"
        """
        return {key: list(stat.items) for key, stat in self.stats.items()}
