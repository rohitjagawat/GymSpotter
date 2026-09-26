"""Exercise-specific constructors using the shared tracking engine."""
from core.base_exercise import BaseExercise


class PushUpDetector(BaseExercise):
    def __init__(self, sets=3, amount=10, rest=30):
        super().__init__('Push-ups', sets=sets, amount=amount, rest=rest)


class PlankDetector(BaseExercise):
    def __init__(self, sets=3, amount=10, rest=30):
        super().__init__('Plank', sets=sets, amount=amount, rest=rest)
