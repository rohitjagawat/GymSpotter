"""Exercise-specific constructors using the shared tracking engine."""
from core.base_exercise import BaseExercise


class ShoulderPressDetector(BaseExercise):
    def __init__(self, sets=3, amount=10, rest=30):
        super().__init__('Shoulder Press', sets=sets, amount=amount, rest=rest)


class LateralRaiseDetector(BaseExercise):
    def __init__(self, sets=3, amount=10, rest=30):
        super().__init__('Lateral Raises', sets=sets, amount=amount, rest=rest)


class FrontRaiseDetector(BaseExercise):
    def __init__(self, sets=3, amount=10, rest=30):
        super().__init__('Front Raises', sets=sets, amount=amount, rest=rest)


class TricepsExtensionDetector(BaseExercise):
    def __init__(self, sets=3, amount=10, rest=30):
        super().__init__('Overhead Triceps Extensions', sets=sets, amount=amount, rest=rest)
