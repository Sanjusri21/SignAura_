from typing import Dict, Any, List

class AvatarAnimatorService:
    """Provides animation assets and skeleton joint mappings for the SignAvatar 3D engine."""

    PRESET_POSES = {
        "rest": {
            "name": "Rest / Neutral",
            "leftArm": {"shoulder": [0, 0, 0], "elbow": [0, 0, 0], "wrist": [0, 0, 0], "fingers": 0},
            "rightArm": {"shoulder": [0, 0, 0], "elbow": [0, 0, 0], "wrist": [0, 0, 0], "fingers": 0},
            "head": [0, 0, 0],
            "expression": "neutral"
        },
        "hello": {
            "name": "Hello Salute",
            "leftArm": {"shoulder": [0, 0, 0], "elbow": [0, 0, 0], "wrist": [0, 0, 0], "fingers": 0},
            "rightArm": {"shoulder": [0.6, 0.4, 0.2], "elbow": [1.4, 0.2, 0.1], "wrist": [0.3, 0.2, 0.4], "fingers": 0.8},
            "head": [0.05, 0, 0],
            "expression": "smile"
        },
        "question": {
            "name": "Questioning Pose",
            "leftArm": {"shoulder": [0.4, -0.2, 0.3], "elbow": [0.8, 0.5, 0.2], "wrist": [0.2, 0.1, 0.3], "fingers": 0.5},
            "rightArm": {"shoulder": [0.4, 0.2, -0.3], "elbow": [0.8, -0.5, -0.2], "wrist": [0.2, -0.1, -0.3], "fingers": 0.5},
            "head": [0.1, 0.1, 0.05],
            "expression": "question"
        },
        "thanks": {
            "name": "Thank You Gesture",
            "leftArm": {"shoulder": [0, 0, 0], "elbow": [0, 0, 0], "wrist": [0, 0, 0], "fingers": 0},
            "rightArm": {"shoulder": [0.5, 0.1, 0.1], "elbow": [1.2, 0.1, 0.2], "wrist": [0.1, 0.3, 0.2], "fingers": 0.9},
            "head": [0.08, 0, 0],
            "expression": "smile"
        }
    }

    @classmethod
    def get_pose_by_gloss(cls, gloss: str) -> Dict[str, Any]:
        g = gloss.strip().lower()
        if "hello" in g or "hi" in g:
            return cls.PRESET_POSES["hello"]
        if "thank" in g:
            return cls.PRESET_POSES["thanks"]
        if "how" in g or "what" in g or "where" in g or "why" in g:
            return cls.PRESET_POSES["question"]
        return cls.PRESET_POSES["rest"]

avatar_animator = AvatarAnimatorService()
