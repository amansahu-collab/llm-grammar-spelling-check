from .base import BaseAggregator

class ContentAggregator(BaseAggregator):

    def aggregate(self, signals: dict, rules: dict) -> dict:
        # content_percentage comes as 0–100
        percentage = signals.get("content_percentage", 0)
        max_score = rules["max_score"]

        score = (percentage / 100) * max_score

        return {
            "score": round(score, 2),
            "feedback": signals.get("feedback", ""),
            "missing_ideas": signals.get("missing_ideas", [])
        }
