"""Constants for the CMS app"""

import enum

COURSE_INDEX_SLUG = "courses"
PROGRAM_INDEX_SLUG = "programs"
SIGNATORY_INDEX_SLUG = "signatories"
CERTIFICATE_INDEX_SLUG = "certificate"
WEBINAR_INDEX_SLUG = "webinars"
BLOG_INDEX_SLUG = "blog"
ENTERPRISE_PAGE_SLUG = "enterprise"

ALL_TOPICS = "All Topics"
ALL_TAB = "all-tab"

# ************** CONSTANTS FOR WEBINARS **************

UPCOMING_WEBINAR = "UPCOMING"
ON_DEMAND_WEBINAR = "ON-DEMAND"
WEBINAR_DEFAULT_IMAGES = [
    "images/webinars/webinar-default-001.jpg",
    "images/webinars/webinar-default-002.jpg",
    "images/webinars/webinar-default-003.jpg",
    "images/webinars/webinar-default-004.jpg",
    "images/webinars/webinar-default-005.jpg",
]
WEBINAR_HEADER_BANNER = "images/webinars/webinar-header-banner.jpg"
UPCOMING_WEBINAR_BUTTON_TITLE = "RESERVE YOUR SEAT"
ON_DEMAND_WEBINAR_BUTTON_TITLE = "VIEW RECORDING"

FORMAT_ONLINE = "Online"
FORMAT_HYBRID = "Hybrid"
FORMAT_OTHER = "Other"

HOW_YOU_WILL_LEARN_SECTION = {
    "title": "HOW YOU WILL LEARN",
    "technique_items": [
        {
            "type": "techniques",
            "value": {
                "heading": "LEARN BY DOING",
                "sub_heading": "Practice processes and methods through simulations, assessments, case studies, and tools.",
                "image": "static/images/how_you_will_learn/idea.png",
            },
        },
        {
            "type": "techniques",
            "value": {
                "heading": "LEARN FROM OTHERS",
                "sub_heading": "Connect with an international community of professionals while working on projects based on real-world examples.",
                "image": "static/images/how_you_will_learn/network.png",
            },
        },
        {
            "type": "techniques",
            "value": {
                "heading": "LEARN ON DEMAND",
                "sub_heading": "Access all of the content online and watch videos on the go.",
                "image": "static/images/how_you_will_learn/work-balance.png",
            },
        },
        {
            "type": "techniques",
            "value": {
                "heading": "REFLECT AND APPLY",
                "sub_heading": "Bring your new skills to your organization, through examples from technical work environments and ample prompts for reflection.",
                "image": "static/images/how_you_will_learn/feedback.png",
            },
        },
        {
            "type": "techniques",
            "value": {
                "heading": "DEMONSTRATE YOUR SUCCESS",
                "sub_heading": "Earn a Professional Certificate and CEUs from MIT xPRO.",
                "image": "static/images/how_you_will_learn/certificate.png",
            },
        },
        {
            "type": "techniques",
            "value": {
                "heading": "LEARN FROM THE BEST",
                "sub_heading": "Gain insights from leading MIT faculty and industry experts.",
                "image": "static/images/how_you_will_learn/trend-speaker.png",
            },
        },
    ],
}

B2B_SECTION = {
    "title": "THE BEST COMPANIES CONNECT WITH THE BEST MINDS AT MIT",
    "content": """
    <p>Deepen your team's career knowledge and expand their abilities with MIT xPRO's online courses for professionals. Develop customized learning for your team with bespoke courses and programs on your schedule. Set a standard of knowledge and skills, leading to effective communication among employees and consistency across the enterprise.</p>

    <p>Find out what MIT xPRO can do for your team.</p>

    """,
    "action_title": "INQUIRE NOW",
    "action_url": "https://learn-xpro.mit.edu/for-teams#b2bform",
    "image": "static/images/enterprise/enterprise-colab.jpg",
}


class CatalogSorting(enum.Enum):
    """Catalog sorting option"""

    BEST_MATCH = ("best_match", "Best Match")
    START_DATE_ASC = ("start_date_asc", "Start Date")
    PRICE_DESC = ("price_desc", "Price: High-Low")
    PRICE_ASC = ("price_asc", "Price: Low-High")

    def __init__(self, sorting_value, sorting_title):
        """
        A sorting option can have a value and a title.
        """
        self.sorting_value = sorting_value
        self.sorting_title = sorting_title
