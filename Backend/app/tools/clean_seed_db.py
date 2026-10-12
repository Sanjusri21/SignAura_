"""
Database Cleanup and Seeding Tool for SignAura.
Removes test/dummy entries (e.g. 'Test Rickroll'), cleans duplicate records,
formats float durations, and seeds authentic demo projects.
"""

import asyncio
import datetime
import re
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = "mongodb://localhost:27017"
DB_NAME = "signaura"

DEMO_PROJECTS = [
    {
        "id": "proj-keynote-2026",
        "job_id": "job-keynote-2026",
        "user_id": "demo-user-1",
        "title": "AI Accessibility Keynote & Welcome Address",
        "original_file_name": "keynote_accessibility_2026.mp4",
        "video_url": "https://www.youtube.com/watch?v=sample_keynote",
        "status": "completed",
        "progress": 100,
        "duration": 34.5,
        "accuracy": 98.4,
        "language": "en",
        "dialect": "standard",
        "transcript": "Hello and welcome everyone. Today we are proud to introduce SignAura, breaking communication barriers across India with artificial intelligence.",
        "gloss_tokens": [
            {"id": "g-1", "word": "Hello", "gloss": "HELLO", "startTime": 0.0, "endTime": 1.8, "confidence": 0.99, "grammarTag": "GREETING"},
            {"id": "g-2", "word": "welcome", "gloss": "WELCOME", "startTime": 1.9, "endTime": 3.5, "confidence": 0.98, "grammarTag": "GREETING"},
            {"id": "g-3", "word": "everyone", "gloss": "ALL-PEOPLE", "startTime": 3.6, "endTime": 5.2, "confidence": 0.97, "grammarTag": "OBJECT"},
            {"id": "g-4", "word": "Today", "gloss": "TODAY", "startTime": 5.3, "endTime": 7.0, "confidence": 0.99, "grammarTag": "TIME_MARKER"},
            {"id": "g-5", "word": "introduce", "gloss": "INTRODUCE", "startTime": 7.1, "endTime": 9.2, "confidence": 0.96, "grammarTag": "VERB"},
            {"id": "g-6", "word": "SignAura", "gloss": "SIGN_LANGUAGE", "startTime": 9.3, "endTime": 11.5, "confidence": 0.98, "grammarTag": "NOUN"},
            {"id": "g-7", "word": "barrier", "gloss": "HELP", "startTime": 11.6, "endTime": 14.0, "confidence": 0.95, "grammarTag": "VERB"},
            {"id": "g-8", "word": "India", "gloss": "INDIA", "startTime": 14.1, "endTime": 16.8, "confidence": 0.99, "grammarTag": "LOCATION"}
        ],
        "created_at": (datetime.datetime.utcnow() - datetime.timedelta(hours=2)).isoformat()
    },
    {
        "id": "proj-medical-triage",
        "job_id": "job-medical-triage",
        "user_id": "demo-user-1",
        "title": "Hospital Emergency First Responder Guide",
        "original_file_name": "emergency_medical_triage.mp4",
        "video_url": "https://www.youtube.com/watch?v=sample_hospital",
        "status": "completed",
        "progress": 100,
        "duration": 48.0,
        "accuracy": 99.1,
        "language": "en",
        "dialect": "standard",
        "transcript": "Doctor is coming immediately. Please stay calm and tell me where it hurts so we can help you.",
        "gloss_tokens": [
            {"id": "g-201", "word": "Doctor", "gloss": "DOCTOR", "startTime": 0.0, "endTime": 2.2, "confidence": 0.99, "grammarTag": "SUBJECT"},
            {"id": "g-202", "word": "coming", "gloss": "COME", "startTime": 2.3, "endTime": 4.5, "confidence": 0.98, "grammarTag": "VERB"},
            {"id": "g-203", "word": "Please", "gloss": "PLEASE", "startTime": 4.6, "endTime": 6.8, "confidence": 0.99, "grammarTag": "MODIFIER"},
            {"id": "g-204", "word": "help", "gloss": "HELP", "startTime": 6.9, "endTime": 9.0, "confidence": 0.99, "grammarTag": "VERB"}
        ],
        "created_at": (datetime.datetime.utcnow() - datetime.timedelta(days=1)).isoformat()
    },
    {
        "id": "proj-fable-cottage",
        "job_id": "job-fable-cottage",
        "user_id": "demo-user-1",
        "title": "The Bear and the Bee - English Fable",
        "original_file_name": "The Bear and the Bee - US English accent (TheFableCottage.com).mp4",
        "video_url": "https://www.youtube.com/watch?v=jKi2SvWOCXc",
        "status": "completed",
        "progress": 100,
        "duration": 185.4,
        "accuracy": 98.7,
        "language": "en",
        "dialect": "standard",
        "transcript": "A hungry bear is exploring the forest looking for delicious sweet honey from the bees.",
        "gloss_tokens": [
            {"id": "g-301", "word": "Forest", "gloss": "FOREST", "startTime": 0.0, "endTime": 2.4, "confidence": 0.97, "grammarTag": "LOCATION"},
            {"id": "g-302", "word": "Bear", "gloss": "BEAR", "startTime": 2.5, "endTime": 4.8, "confidence": 0.98, "grammarTag": "SUBJECT"},
            {"id": "g-303", "word": "Food", "gloss": "EAT", "startTime": 4.9, "endTime": 7.2, "confidence": 0.96, "grammarTag": "OBJECT"},
            {"id": "g-304", "word": "Go", "gloss": "GO", "startTime": 7.3, "endTime": 9.5, "confidence": 0.99, "grammarTag": "VERB"}
        ],
        "created_at": (datetime.datetime.utcnow() - datetime.timedelta(days=2)).isoformat()
    }
]

async def clean_and_seed():
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    jobs_col = db["video_jobs"]

    print("Connecting to MongoDB signaura...")

    # 1. Remove obvious test / garbage entries
    test_query = {
        "$or": [
            {"title": {"$regex": r"rickroll|test rickroll|test video", "$options": "i"}},
            {"original_file_name": {"$regex": r"dQw4w9WgXcQ", "$options": "i"}},
        ]
    }
    del_res = await jobs_col.delete_many(test_query)
    print(f"Removed {del_res.deleted_count} test/junk entries (e.g. Test Rickroll).")

    # 2. Find and deduplicate remaining entries based on video_url / original_file_name
    seen_sources = set()
    duplicates_to_delete = []
    
    cursor = jobs_col.find({}).sort("created_at", -1)
    all_jobs = await cursor.to_list(100)

    for job in all_jobs:
        source_key = job.get("video_url") or job.get("original_file_name") or job.get("title")
        if not source_key:
            continue
        # Normalize key
        norm_key = re.sub(r"\s+", " ", str(source_key).strip().lower())
        if norm_key in seen_sources:
            duplicates_to_delete.append(job["_id"])
        else:
            seen_sources.add(norm_key)

    if duplicates_to_delete:
        del_dups = await jobs_col.delete_many({"_id": {"$in": duplicates_to_delete}})
        print(f"Deduplicated {del_dups.deleted_count} duplicate job records.")

    # 3. Clean generic titles ("Web Video Conversion", "Web Stream Video")
    cursor = jobs_col.find({})
    async for job in cursor:
        title = job.get("title", "")
        orig_name = job.get("original_file_name", "")
        transcript = job.get("transcript", "")
        new_title = None

        if title in ("Web Video Conversion", "Web Stream Video", "Web Video Processing", "Online Video Stream"):
            if orig_name and orig_name not in ("Online Video Stream", "media.mp4", "Web Video"):
                # Clean filename
                clean_name = re.sub(r"YouTube Video \([^\)]+\)", "", orig_name).strip()
                clean_name = re.sub(r"\.(mp4|webm|mkv|mov)$", "", clean_name, flags=re.I).strip()
                if clean_name:
                    new_title = clean_name
            elif transcript:
                words = transcript.strip().split()[:7]
                if words:
                    new_title = " ".join(words) + "..."
        
        # Round duration to 1 decimal
        duration = job.get("duration", 0.0)
        new_dur = round(float(duration or 0.0), 1)

        updates = {}
        if new_title and new_title != title:
            updates["title"] = new_title
        if new_dur != duration:
            updates["duration"] = new_dur

        if updates:
            await jobs_col.update_one({"_id": job["_id"]}, {"$set": updates})

    print("Updated generic titles and normalized float durations.")

    # 4. Seed authentic demo projects if missing
    for proj in DEMO_PROJECTS:
        existing = await jobs_col.find_one({"id": proj["id"]})
        if not existing:
            await jobs_col.insert_one(proj)
            print(f"Seeded demo project: {proj['title']}")

    final_count = await jobs_col.count_documents({})
    print(f"Done! Clean database has {final_count} verified projects.")

if __name__ == "__main__":
    asyncio.run(clean_and_seed())
