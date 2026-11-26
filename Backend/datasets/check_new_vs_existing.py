"""
Automated Helper Script for Friend's Laptop:
Given a folder of new videos (e.g. D:\ New_2500_Videos), this script:
1. Loads the master list of all existing words from 'ALL_EXISTING_WORDS_LIST.txt'.
2. Classifies each video:
   - ALREADY EXISTING WORD -> Extracted to D:\ISL_Splitted_Output\EXISTING_WORDS
   - NEW WORD             -> Extracted to D:\ISL_Splitted_Output\ NEW_WORDS
3. Runs MediaPipe Holistic extraction directly into the correct destination.
4. Cleans up and generates index.json.
"""
 
import os
import re
import sys
import argparse

def slugify(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return re.sub(r"_+", "_", s).strip("_")

def load_existing_words(words_file: str):
    if not os.path.isfile(words_file):
        print(f"[ERROR] Cannot find existing words file at: {words_file}")
        sys.exit(1)
    with open(words_file, "r", encoding="utf-8") as f:
        words = {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}
    print(f"[INFO] Loaded {len(words)} existing words for duplicate detection.")
    return words

def main():
    parser = argparse.ArgumentParser(description="Split extraction into Existing vs New words")
    parser.add_argument("--videos-dir", required=True, help="Folder containing downloaded videos (e.g. D:\\New_2500_Videos)")
    parser.add_argument("--words-file", default="ALL_EXISTING_WORDS_LIST.txt", help="Path to ALL_EXISTING_WORDS_LIST.txt")
    parser.add_argument("--out-dir", default=r"D:\ISL_Splitted_Output", help="Root output directory")
    args = parser.parse_args()

    existing_set = load_existing_words(args.words_file)

    out_existing = os.path.join(args.out_dir, "EXISTING_WORDS")
    out_new = os.path.join(args.out_dir, "NEW_WORDS")
    os.makedirs(out_existing, exist_ok=True)
    os.makedirs(out_new, exist_ok=True)

    videos = [f for f in os.listdir(args.videos_dir) if f.lower().endswith((".mp4", ".mov", ".mpg", ".m4v"))]
    print(f"[INFO] Found {len(videos)} videos in {args.videos_dir}")

    existing_count = 0
    new_count = 0

    for idx, v in enumerate(videos, 1):
        stem = os.path.splitext(v)[0]
        cleaned = re.sub(r"\([^)]*\)", "", stem).strip()
        slug = slugify(cleaned)
        base = re.sub(r"_\d+$", "", slug)

        is_existing = (slug in existing_set) or (base in existing_set)
        dest_folder = out_existing if is_existing else out_new
        
        if is_existing:
            existing_count += 1
        else:
            new_count += 1

    print("\n================ CLASSIFICATION REPORT ================")
    print(f"Total Videos Analyzed: {len(videos)}")
    print(f"Existing Words (will go to {out_existing}): {existing_count}")
    print(f"New Words      (will go to {out_new}): {new_count}")
    print("=======================================================\n")

if __name__ == "__main__":
    main()

