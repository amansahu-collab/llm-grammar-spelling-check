from .base import BaseAggregator

class ContentAggregator(BaseAggregator):

    def aggregate(self, signals: dict, rules: dict) -> dict:
        # Return model output as-is without any changes
        return signals
