"""MHR's 72 face expressions as the face's controls (#226), each mapped onto ICT-FaceKit's ARKit-named expressions.

MHR v1's names and order are facebookresearch/MHR docs/face-expressions.md's (`_L`/`_R` the character's sides, as
ICT-FaceKit's are). `ICT_OF` gives each MHR expression the ICT expressions that make it on the detail face, with
their weights; an expression with no ICT counterpart (cheekSuck, lipTightener, nasolabialFurrow, nostrilCompressor,
nostrilDilator) moves the detail face by the body's own MHR offsets under it (`face.py`), so every control moves the
face. A look's side for the eyes: looking to the character's left is the left eye's look out and the right eye's in.
"""
import numpy as np

MHR_EXPRESSIONS = (
    "browLowerer_L", "browLowerer_R", "cheekPuff_L", "cheekPuff_R", "cheekRaiser_L", "cheekRaiser_R", "cheekSuck_L",
    "cheekSuck_R", "chinRaiser_B", "chinRaiser_T", "dimpler_L", "dimpler_R", "eyesClosed_L", "eyesClosed_R",
    "eyesLookDown_L", "eyesLookDown_R", "eyesLookLeft_L", "eyesLookLeft_R", "eyesLookRight_L", "eyesLookRight_R",
    "eyesLookUp_L", "eyesLookUp_R", "innerBrowRaiser_L", "innerBrowRaiser_R", "jawDrop", "jawSidewaysLeft",
    "jawSidewaysRight", "jawThrust", "lidTightener_L", "lidTightener_R", "lipCornerDepressor_L",
    "lipCornerDepressor_R", "lipCornerPuller_L", "lipCornerPuller_R", "lipFunneler_LB", "lipFunneler_LT",
    "lipFunneler_RB", "lipFunneler_RT", "lipPressor_L", "lipPressor_R", "lipPucker_L", "lipPucker_R",
    "lipStretcher_L", "lipStretcher_R", "lipSuck_LB", "lipSuck_LT", "lipSuck_RB", "lipSuck_RT", "lipTightener_L",
    "lipTightener_R", "lipsToward_LB", "lipsToward_LT", "lipsToward_RB", "lipsToward_RT", "lowerLipDepressor_L",
    "lowerLipDepressor_R", "mouthLeft", "mouthRight", "nasolabialFurrow_L", "nasolabialFurrow_R", "noseWrinkler_L",
    "noseWrinkler_R", "nostrilCompressor_L", "nostrilCompressor_R", "nostrilDilator_L", "nostrilDilator_R",
    "outerBrowRaiser_L", "outerBrowRaiser_R", "upperLidRaiser_L", "upperLidRaiser_R", "upperLipRaiser_L",
    "upperLipRaiser_R")

SIDED = {"browLowerer": "browDown", "cheekPuff": "cheekPuff", "cheekRaiser": "cheekSquint", "dimpler": "mouthDimple",
         "eyesClosed": "eyeBlink", "eyesLookDown": "eyeLookDown", "eyesLookUp": "eyeLookUp",
         "innerBrowRaiser": "browInnerUp", "lidTightener": "eyeSquint", "lipCornerDepressor": "mouthFrown",
         "lipCornerPuller": "mouthSmile", "lipPressor": "mouthPress", "lipStretcher": "mouthStretch",
         "lowerLipDepressor": "mouthLowerDown", "noseWrinkler": "noseSneer", "outerBrowRaiser": "browOuterUp",
         "upperLidRaiser": "eyeWide", "upperLipRaiser": "mouthUpperUp"}
ICT_OF = {**{f"{mhr}_{side}": {f"{ict}_{side}": 1.0} for mhr, ict in SIDED.items() for side in "LR"},
          "chinRaiser_B": {"mouthShrugLower": 1.0}, "chinRaiser_T": {"mouthShrugUpper": 1.0},
          "eyesLookLeft_L": {"eyeLookOut_L": 1.0}, "eyesLookLeft_R": {"eyeLookIn_R": 1.0},
          "eyesLookRight_L": {"eyeLookIn_L": 1.0}, "eyesLookRight_R": {"eyeLookOut_R": 1.0},
          "jawDrop": {"jawOpen": 1.0}, "jawSidewaysLeft": {"jawLeft": 1.0}, "jawSidewaysRight": {"jawRight": 1.0},
          "jawThrust": {"jawForward": 1.0},
          **{f"lipFunneler_{quarter}": {"mouthFunnel": 0.25} for quarter in ("LB", "LT", "RB", "RT")},
          "lipPucker_L": {"mouthPucker": 0.5}, "lipPucker_R": {"mouthPucker": 0.5},
          "lipSuck_LB": {"mouthRollLower": 0.5}, "lipSuck_RB": {"mouthRollLower": 0.5},
          "lipSuck_LT": {"mouthRollUpper": 0.5}, "lipSuck_RT": {"mouthRollUpper": 0.5},
          **{f"lipsToward_{quarter}": {"mouthClose": 0.25} for quarter in ("LB", "LT", "RB", "RT")},
          "mouthLeft": {"mouthLeft": 1.0}, "mouthRight": {"mouthRight": 1.0}}


def mapping(ict_names):
    """The (72, ICT expressions) weights taking MHR's controls to ICT's expressions, refusing a name ICT lacks."""
    ict_names = [str(name) for name in ict_names]
    matrix = np.zeros((len(MHR_EXPRESSIONS), len(ict_names)))
    for row, mhr in enumerate(MHR_EXPRESSIONS):
        for ict, weight in ICT_OF.get(mhr, {}).items():
            if ict not in ict_names:
                raise KeyError(f"{mhr} maps to {ict}, which ICT-FaceKit does not have")
            matrix[row, ict_names.index(ict)] = weight
    return matrix
