from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.schemas.isl import GlossTokenSchema, ISLTranslateResponse

class ISLServiceBase(ABC):
    """
    Abstract Base Class for Indian Sign Language (ISL) Translation Providers.
    Allows easy plug-and-play integration of custom neural ISL models or real ISL datasets.
    """
    @abstractmethod
    async def translate_to_gloss(self, text: str, dialect: str = "standard") -> ISLTranslateResponse:
        """
        Convert English/Indian English text to an ordered ISL Gloss token sequence with animations.
        """
        pass

    @abstractmethod
    async def get_animation_mapping(self, gloss: str) -> str:
        """
        Map an ISL gloss word to its corresponding 3D .glb animation asset or fallback fingerspelling.
        """
        pass
