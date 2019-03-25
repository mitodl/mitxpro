"""Courseware constants"""

PLATFORM_EDX = "edx"
# List of all currently-supported courseware platforms
COURSEWARE_PLATFORMS = (PLATFORM_EDX,)
# Currently-supported courseware platforms in a ChoiceField-friendly format
COURSEWARE_PLATFORM_CHOICES = zip(COURSEWARE_PLATFORMS, COURSEWARE_PLATFORMS)
