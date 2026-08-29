from typing import Dict, List, Any

# Curated Indian Sign Language Dictionary with standardized gloss representations
ISL_DICTIONARY: List[Dict[str, Any]] = [
    {
        "id": "dict-1",
        "word": "hello",
        "gloss": "HELLO",
        "category": "Greetings",
        "definition": "Open hand raised to forehead and extended outward in a polite salute gesture.",
        "exampleSentence": "Hello! Welcome to our inclusive session.",
        "difficulty": "Beginner",
        "animationFile": "hello.glb"
    },
    {
        "id": "dict-2",
        "word": "how",
        "gloss": "HOW",
        "category": "Conversational",
        "definition": "Cupped hands palms-up rotating outward with questioning facial expression.",
        "exampleSentence": "How are you doing today?",
        "difficulty": "Beginner",
        "animationFile": "how.glb"
    },
    {
        "id": "dict-3",
        "word": "are",
        "gloss": "ARE",
        "category": "Conversational",
        "definition": "Auxiliary state marker gesture in English-ISL bridge.",
        "exampleSentence": "How are you?",
        "difficulty": "Beginner",
        "animationFile": "are.glb"
    },
    {
        "id": "dict-4",
        "word": "you",
        "gloss": "YOU",
        "category": "Conversational",
        "definition": "Direct index finger pointing toward conversational partner.",
        "exampleSentence": "Nice to meet you.",
        "difficulty": "Beginner",
        "animationFile": "you.glb"
    },
    {
        "id": "dict-5",
        "word": "thank you",
        "gloss": "THANK_YOU",
        "category": "Greetings",
        "definition": "Flat hand moving from chin forward toward the listener.",
        "exampleSentence": "Thank you for your warm assistance.",
        "difficulty": "Beginner",
        "animationFile": "thank_you.glb"
    },
    {
        "id": "dict-6",
        "word": "welcome",
        "gloss": "WELCOME",
        "category": "Greetings",
        "definition": "Both hands open swept inwards toward the torso in welcoming motion.",
        "exampleSentence": "Welcome to SignAura.",
        "difficulty": "Beginner",
        "animationFile": "welcome.glb"
    },
    {
        "id": "dict-7",
        "word": "help",
        "gloss": "HELP",
        "category": "Emergency",
        "definition": "Closed fist with thumb up resting on open palm of other hand, moving upward.",
        "exampleSentence": "Please call emergency help.",
        "difficulty": "Beginner",
        "animationFile": "help.glb"
    },
    {
        "id": "dict-8",
        "word": "emergency",
        "gloss": "EMERGENCY",
        "category": "Emergency",
        "definition": "Shaking 'E' handshape across chest area with urgency.",
        "exampleSentence": "There is a medical emergency here.",
        "difficulty": "Intermediate",
        "animationFile": "emergency.glb"
    },
    {
        "id": "dict-9",
        "word": "doctor",
        "gloss": "DOCTOR",
        "category": "Medical",
        "definition": "Tapping radial pulse on wrist with two fingers of dominant hand.",
        "exampleSentence": "The doctor is reviewing the report.",
        "difficulty": "Beginner",
        "animationFile": "doctor.glb"
    },
    {
        "id": "dict-10",
        "word": "hospital",
        "gloss": "HOSPITAL",
        "category": "Medical",
        "definition": "Drawing a cross shape on shoulder with index finger.",
        "exampleSentence": "Where is the nearest hospital?",
        "difficulty": "Intermediate",
        "animationFile": "hospital.glb"
    },
    {
        "id": "dict-11",
        "word": "india",
        "gloss": "INDIA",
        "category": "Education",
        "definition": "Thumb touched to center of forehead (Bindi placement) moving slightly outward.",
        "exampleSentence": "Indian Sign Language connects millions across India.",
        "difficulty": "Beginner",
        "animationFile": "india.glb"
    },
    {
        "id": "dict-12",
        "word": "accessible",
        "gloss": "ACCESSIBLE",
        "category": "Technology",
        "definition": "Interlocking circular hand movements symbolizing universal access.",
        "exampleSentence": "Making digital media accessible for everyone.",
        "difficulty": "Advanced",
        "animationFile": "accessible.glb"
    },
    {
        "id": "dict-13",
        "word": "sign language",
        "gloss": "SIGN_LANGUAGE",
        "category": "Education",
        "definition": "Alternate circular rotating hands in front of chest.",
        "exampleSentence": "Learning sign language empowers community communication.",
        "difficulty": "Beginner",
        "animationFile": "sign_language.glb"
    }
]

def get_dictionary_item_by_word(word: str) -> Dict[str, Any]:
    w = word.strip().lower()
    for item in ISL_DICTIONARY:
        if item["word"].lower() == w or item["gloss"].lower() == w:
            return item
    return None
