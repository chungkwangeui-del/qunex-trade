"""Lightweight shap stub for testing environments."""

__all__ = ["ExplainableModel"]


class ExplainableModel:
    def __init__(self, *_, **__):
        self.explanations = []

    def explain(self, *_, **__):
        return {"explanations": self.explanations}
