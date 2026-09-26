"""The 12 supported exercises, in the project's existing detector layout."""
from core.base_exercise import BaseExercise
from detectors.squats import SquatDetector, WallSitDetector
from detectors.pushup import PushUpDetector, PlankDetector
from detectors.biceps_curl import BicepsCurlDetector
from detectors.shoulder_press import ShoulderPressDetector, LateralRaiseDetector, FrontRaiseDetector, TricepsExtensionDetector
from detectors.lunges import LungesDetector, KneeRaiseDetector

class JumpingJackDetector(BaseExercise):
    def __init__(self, sets=3, amount=10, rest=30):
        super().__init__('Jumping Jacks', sets=sets, amount=amount, rest=rest)

DETECTORS = {
    'Squats': SquatDetector,
    'Wall Sit': WallSitDetector,
    'Push-ups': PushUpDetector,
    'Plank': PlankDetector,
    'Biceps Curls (Dumbbell)': BicepsCurlDetector,
    'Shoulder Press': ShoulderPressDetector,
    'Lateral Raises': LateralRaiseDetector,
    'Front Raises': FrontRaiseDetector,
    'Overhead Triceps Extensions': TricepsExtensionDetector,
    'Lunges': LungesDetector,
    'Standing Knee Raises': KneeRaiseDetector,
    'Jumping Jacks': JumpingJackDetector,
}

def create_detector(exercise, sets=3, amount=10, rest=30):
    return DETECTORS[exercise](sets=sets, amount=amount, rest=rest)
