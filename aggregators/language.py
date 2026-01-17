from .base import BaseAggregator

class LanguageAggregator(BaseAggregator):

    def aggregate(self, signals: dict, rules: dict) -> dict:
        grammar_errors = len(signals.get("grammar_errors", []))
        spelling_errors = signals.get("spelling", {}).get("count", 0)
        mechanics_errors = len(signals.get("mechanics_errors", []))

        total_errors = grammar_errors + spelling_errors + mechanics_errors

        grammar_max = rules["grammar_max"]
        spelling_max = rules["spelling_max"]
        penalty = rules["penalty_per_error"]

        grammar_score = max(grammar_max - (grammar_errors * penalty), 0)
        spelling_score = max(spelling_max - (spelling_errors * penalty), 0)

        return {
            "grammar_score": round(grammar_score, 2),
            "spelling_score": round(spelling_score, 2),
            "total_errors": total_errors
        }
