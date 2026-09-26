"""Exercise-specific constructors using the shared tracking engine."""
from core.base_exercise import BaseExercise


class SquatDetector(BaseExercise):
    def __init__(self, sets=3, amount=10, rest=30):
        super().__init__('Squats', sets=sets, amount=amount, rest=rest)


class WallSitDetector(BaseExercise):
    def __init__(self, sets=3, amount=10, rest=30):
        super().__init__('Wall Sit', sets=sets, amount=amount, rest=rest)
