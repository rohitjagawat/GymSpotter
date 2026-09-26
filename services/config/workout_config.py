from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "ml_models" / "pose_landmarker_full.task"

# Thresholds are engineering heuristics, not clinically validated standards.
EXERCISES = {
    "Squats": dict(group="Lower body", view="Side", kind="reps", start=165, end=90,
        cue="Stand side-on with your full body visible. Sit down and back, then stand tall.",
        checks="Depth · torso lean · tempo"),
    "Push-ups": dict(group="Upper body", view="Side", kind="reps", start=165, end=85,
        cue="Place the camera at your side. Keep shoulders, hips and ankles visible.",
        checks="Elbow range · hip sag/pike · tempo"),
    "Biceps Curls (Dumbbell)": dict(group="Upper body", view="Side", kind="reps", start=150, end=50, view_advisory=True,
        cue="Keep shoulder, elbow and wrist visible, preferably at a slight side angle. Lower your hand first, then curl and lower to count.",
        checks="Elbow drift · torso lean · range · tempo"),
    "Shoulder Press": dict(group="Upper body", view="Front", kind="reps", start=85, end=165,
        cue="Face the camera. Keep both wrists and your hips visible throughout the press.",
        checks="Arm extension · left/right timing · torso tilt · tempo"),
    "Lunges": dict(group="Lower body", view="Side", kind="reps", start=165, end=90,
        cue="Use a stationary split stance, side-on. Finish a set before changing legs.",
        checks="Front-knee range · torso lean · tempo"),
    "Lateral Raises": dict(group="Upper body", view="Front", kind="reps", start=10, end=85,
        cue="Face the camera. Raise both arms sideways toward shoulder height, then lower.",
        checks="Raise height · asymmetry · torso tilt · tempo"),
    "Front Raises": dict(group="Upper body", view="Side", kind="reps", start=10, end=85,
        cue="Stand side-on. Raise your arms forward toward shoulder height, then lower.",
        checks="Raise height · excessive elbow bend · torso lean · tempo"),
    "Overhead Triceps Extensions": dict(group="Upper body", view="Side", kind="reps", start=165, end=65,
        cue="Stand side-on, upper arms overhead. Bend your elbows, then extend them.",
        checks="Elbow range · upper-arm position · torso lean · tempo"),
    "Jumping Jacks": dict(group="Conditioning", view="Front", kind="reps", start=15, end=150,
        cue="Face the camera with space around you. Open arms and feet together, then close.",
        checks="Arm range · foot opening · left/right timing"),
    "Standing Knee Raises": dict(group="Conditioning", view="Side", kind="reps", start=170, end=90,
        cue="Stand side-on. Raise and lower the same knee for one set, then switch legs.",
        checks="Knee height · torso lean · tempo"),
    "Plank": dict(group="Core", view="Side", kind="hold", start=0, end=0,
        cue="Place the camera side-on. Hold a forearm plank with your full body visible.",
        checks="Body line · hip sag/pike · valid hold time"),
    "Wall Sit": dict(group="Lower body", view="Side", kind="hold", start=0, end=0,
        cue="With your back against a wall, face sideways to the camera and hold your seated position.",
        checks="Knee-angle band · torso lean · valid hold time"),
}
CONNECTIONS = [(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),
               (23,24),(23,25),(25,27),(24,26),(26,28),(27,31),(28,32)]


def get_setting(name,default=''):
    import os
    import streamlit as st
    value=os.environ.get(name)
    if value: return value
    try: return str(st.secrets.get(name,default))
    except (FileNotFoundError,st.errors.StreamlitSecretNotFoundError): return default



EXERCISE_OPTIONS = list(EXERCISES)
POSE_CONNECTIONS = CONNECTIONS
