from abc import ABC, abstractmethod

class BaseAggregator(ABC):

    @abstractmethod
    def aggregate(self, signals: dict, rules: dict) -> dict:
        """
        signals: raw service output
        rules: aggregation rules from test yaml
        return: { score, feedback?, debug? }
        """
        pass
