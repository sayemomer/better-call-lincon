"""
Fixed prompt set for the immigration consultant chat UI.

Categories and prompts are returned by GET /api/v1/chat/prompts.
"""

from typing import TypedDict


class PromptCategory(TypedDict):
    id: str
    name: str
    prompts: list[str]


FIXED_PROMPT_CATEGORIES: list[PromptCategory] = [
    {
        "id": "crs_score",
        "name": "CRS Score",
        "prompts": [
            "What is my CRS score?",
            "How can I increase my CRS score?",
            "Is my profile competitive?",
            "Should I retake IELTS?",
            "Does French increase my score?",
            "Should my spouse take IELTS?",
        ],
    },
    {
        "id": "eligibility",
        "name": "Eligibility",
        "prompts": [
            "Am I eligible for CEC?",
            "Am I eligible for FSW?",
            "What is proof of funds requirement?",
            "Do I need ECA?",
        ],
    },
    {
        "id": "timeline",
        "name": "Timeline",
        "prompts": [
            "When is the next draw?",
            "What are recent CRS cutoffs?",
            "How long does PR processing take?",
        ],
    },
    {
        "id": "pnp",
        "name": "PNP Questions",
        "prompts": [
            "Which province is best for my profile?",
            "What PNP streams match my job?",
            "Does my NOC qualify?",
            "Can I apply without job offer?",
            "How long does PNP take?",
        ],
    },
    {
        "id": "status_expiry_deadlines",
        "name": "Status, Expiry & Deadlines",
        "prompts": [
            "When does my permit expire?",
            "When should I apply for extension?",
            "What is implied status?",
            "What happens if I overstay?",
            "How many days before expiry should I apply?",
        ],
    },
]


def get_fixed_prompts() -> list[PromptCategory]:
    """Return the fixed prompt categories for the chat UI."""
    return FIXED_PROMPT_CATEGORIES.copy()
