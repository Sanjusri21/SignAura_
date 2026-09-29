import sys
from pathlib import Path

# Add project root and Backend to sys.path
root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "Backend"))
sys.path.insert(0, str(root / "SignAvatars"))

from app.services.isign.retrieval import isign_pose_retriever
from app.services.isign.motion_service import isign_motion_service

uids = ["FyPkQyJWsjs--100", "60c9973b69ed-43", "zyvXu0nLgFI--18"]
for uid in uids:
    print(f"Reprocessing {uid} with force_refresh=True...")
    res = isign_pose_retriever.process_uid(uid, force_refresh=True)
    print(f"{uid}: success={res['success']}")

print("\nRegenerating motion for 'Fancy staying back again.'...")
motion_res = isign_motion_service.translate_to_motion("Fancy staying back again.")
print(f"Motion available={motion_res['available']}, frames={motion_res['frames']}")
