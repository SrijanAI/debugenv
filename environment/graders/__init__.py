from .base import BaseGrader
from .easy import EasyGrader
from .medium import MediumGrader
from .hard import HardGrader

GRADERS = {
    "easy": EasyGrader,
    "medium": MediumGrader,
    "hard": HardGrader,
}
