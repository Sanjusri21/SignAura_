import datetime
import uuid
from typing import Dict, Any, List
from app.core.config import settings
from app.services.isl.service import get_isl_service

class AIAssistantService:
    """Conversational AI Assistant with integrated ISL gloss generation."""

    @classmethod
    async def generate_response(cls, message: str, dialect: str = "standard") -> Dict[str, Any]:
        msg_lower = message.lower().strip()
        isl_service = get_isl_service()

        # Handle common conversational queries
        if "emergency" in msg_lower or "help" in msg_lower or "ambulance" in msg_lower:
            reply_text = "For medical emergencies in India, dial 112 or 108. I am signaling the emergency help sign on the avatar."
            rec_signs = ["HELP", "EMERGENCY", "DOCTOR", "HOSPITAL"]
        elif "hello" in msg_lower or "hi" in msg_lower or "hey" in msg_lower:
            reply_text = "Namaste! Welcome to SignAura. How can I assist with Indian Sign Language translation today?"
            rec_signs = ["HELLO", "WELCOME", "SIGN_LANGUAGE", "INDIA"]
        elif "doctor" in msg_lower or "hospital" in msg_lower:
            reply_text = "The sign for DOCTOR is performed by tapping the radial pulse on your wrist with two fingers."
            rec_signs = ["DOCTOR", "HOSPITAL", "HELP"]
        elif "how are you" in msg_lower:
            reply_text = "I am doing well and ready to translate Indian Sign Language for you!"
            rec_signs = ["HELLO", "HOW", "ARE", "YOU"]
        else:
            reply_text = f"I have processed your query: '{message}'. Generating Indian Sign Language gloss sequence and spatial avatar movements."
            rec_signs = ["SIGN_LANGUAGE", "ACCESSIBLE", "INDIA", "THANK_YOU"]

        # Generate ISL gloss for the response
        isl_result = await isl_service.translate_to_gloss(reply_text, dialect=dialect)

        now_str = datetime.datetime.now().strftime("%I:%M %p")
        return {
            "id": f"msg-{uuid.uuid4().hex[:8]}",
            "text": reply_text,
            "timestamp": now_str,
            "glossSequence": isl_result.gloss,
            "recommendedSigns": rec_signs,
            "sender": "ai"
        }

ai_assistant = AIAssistantService()
