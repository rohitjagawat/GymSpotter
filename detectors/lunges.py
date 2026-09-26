"""Exercise-specific constructors using the shared tracking engine."""
from core.base_exercise import BaseExercise


class LungesDetector(BaseExercise):
    def __init__(self, sets=3, amount=10, rest=30):
        super().__init__('Lunges', sets=sets, amount=amount, rest=rest)


class KneeRaiseDetector(BaseExercise):
    def __init__(self, sets=3, amount=10, rest=30):
        super().__init__('Standing Knee Raises', sets=sets, amount=amount, rest=rest)
