# iSign Benchmark Dataset Integration in SignAura

## 1. What iSign Is

The **iSign Benchmark Dataset** ([Exploration-Lab/iSign](https://huggingface.co/datasets/Exploration-Lab/iSign), published at *Findings of ACL 2024*, arXiv:2407.05404) is one of the largest available open-research benchmarks for Indian Sign Language (ISL) processing. It was developed by researchers from IIT Kanpur, Max Planck Institute for Psycholinguistics, ISLRTC (Indian Sign Language Research and Training Center), and Microsoft.

The dataset comprises **118,228 ISL-English video-sentence/phrase pairs** scraped and segmented from three primary authentic channels:
1. **ISLRTC**: Educational and standard ISL content produced by certified signers.
2. **ISH News**: News broadcasts featuring deaf anchors communicating current affairs with English subtitles.
3. **DEF (Deaf Enabled Foundation)**: Word-of-the-day explanations and contextual example sentences.

The benchmark formalizes five core NLP and computer vision tasks:
- **Task 1: ISLVideo2Text & ISLPose2Text**: Continuous sign language translation.
- **Task 2: English-to-ISLPose**: Sign language pose generation.
- **Task 3: Word/Gloss Recognition**: Prototype-based isolated sign classification (CISLR).
- **Task 4: Word Presence Prediction**: Verifying whether a query word appears in an ISL sentence.
- **Task 5: Semantic Similarity Prediction**: Aligning word concepts with continuous sentence descriptions.

---

## 2. Which iSign Files Are Being Used

During our audit of the Hugging Face repository `Exploration-Lab/iSign`, we identified the complete repository file inventory:

| Filename | Type | Size / Archive Structure | Description |
| :--- | :--- | :--- | :--- |
| `iSign_v1.1.csv` | Metadata / Translations | Primary CSV (~118k rows) | Sentence-level translations, UIDs, and splits. |
| `word-presence-dataset_v1.1.csv` | Task 4 Metadata | CSV | Query words, candidate sentence UIDs, and presence labels. |
| `word-description-dataset_v1.1.csv` | Task 5 Metadata | CSV | Query words, definition UIDs, and descriptive text. |
| `iSign-poses_v1.1_part_aa..ad` | Multi-part Pose Archive | 4 split binary parts | MediaPipe Holistic 75 keypoints for each UID segment. |
| `iSign-videos_v1.1_part_aa..ab` | Multi-part Video Archive | 2 split binary parts | Segmented MP4 video clips (`{uid}.mp4`). |

**In SignAura, we strictly enforce Data Authenticity**:
- We query official `iSign_v1.1.csv` and task metadata when installed.
- **Current Installation State**: Because `Exploration-Lab/iSign` is gated on Hugging Face and requires authenticated credentials with research agreement, raw official files are currently absent from `D:\SignAuraData\iSign`.
- **Zero Fabrication Policy**: All synthetic mock rows and randomly generated pose files have been completely purged from `D:\SignAuraData\iSign`. When real files are absent, the service strictly reports `is_available: False` and informs the client that Hugging Face gating credentials are required.
- Unit testing relies exclusively on an in-memory isolated fixture that never writes to production dataset paths.
- Poses and videos are inspected selectively per UID on disk without mass downloads.

---

## 3. Dataset Licensing & Gating Restrictions

- **License**: **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)**.
- **Usage Scope**: Strictly for research, education, and accessibility evaluation. **Commercial usage is prohibited**.
- **Gating**: The Hugging Face repository is gated (`repoIsGated: true`). Users must log in to Hugging Face, agree to research-only conditions, provide institutional affiliation, and accept terms.
- **Redistribution**: SignAura adheres to strict compliance:
  - We **never** bypass the Hugging Face gate.
  - We **never** re-host or re-distribute the raw 228 GB dataset.
  - Large dataset files are **excluded** from Git via `.gitignore`.

---

## 4. Where the Dataset Is Stored

To prevent overflowing the primary Windows drive (`C:`), all iSign assets are organized on secondary high-capacity storage:

```
D:\SignAuraData\iSign\
├── iSign_v1.1.csv                        # Main sentence translation dataset
├── word-presence-dataset_v1.1.csv        # Task 4 presence evaluation pairs
├── word-description-dataset_v1.1.csv     # Task 5 semantic descriptions
├── poses\                                # Individual .pose / .npz files ({uid}.npz)
└── videos\                               # Individual .mp4 video clips ({uid}.mp4)
```

Configuration environment variables:
- `ISIGN_DATA_DIR`: default `D:\SignAuraData\iSign`
- `ISIGN_METADATA_PATH`: default `D:\SignAuraData\iSign\iSign_v1.1.csv`
- `ISIGN_POSES_DIR`: default `D:\SignAuraData\iSign\poses`
- `ISIGN_VIDEOS_DIR`: default `D:\SignAuraData\iSign\videos`
- `ISIGN_ENABLED`: `true`

---

## 5. Metadata Schema

Every record in `iSign_v1.1.csv` follows the official benchmark schema:

| Field Name | Type | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `uid` | String | `1782bea75c7d-7` | Unique identifier structured as `[video_id]-[sequence_number]`. |
| `video_id` | String | `1782bea75c7d` | Hash of source YouTube broadcast / educational video. |
| `sequence_number` | Integer | `7` | Chronological segment index of utterance within source video. |
| `text` | String | `"The students are sitting in the classroom quietly."` | English translation of the signed segment. |
| `split` | String | `"test"` | Dataset partition: `train`, `dev`, or `test`. |
| `source` | String | `"ISLRTC"` | Content creator: `ISLRTC`, `ISH`, or `DEF`. |

---

## 6. iSign → BridgeConn Semantic Mapping & Taxonomy

Because iSign provides continuous sentence-level utterances while BridgeConn provides authenticated 3D SMPL-X motion captures, SignAura establishes a deterministic mapping layer (`Backend/app/services/isign/mapper.py`).

Every extracted word token is strictly classified into one of four categories:

1. **`EXACT_BRIDGECONN_MATCH`**:
   - The token directly matches a validated canonical sign in the BridgeConn dictionary.
   - *Example*: `"drink"` $\to$ `DRINK` (available in BridgeConn).
2. **`VARIANT_BRIDGECONN_MATCH`**:
   - The token is an inflectional, tense, or plural variant of a known sign.
   - *Example*: `"drinking"`, `"drank"` $\to$ `DRINK`; `"helped"`, `"helps"` $\to$ `HELP_2`.
3. **`PARTIAL_MATCH`**:
   - The token is a compound word sharing a discrete sign root.
   - *Example*: `"classroom"` $\to$ `CLASS` (partial).
4. **`NO_BRIDGECONN_MATCH`**:
   - The sign is absent from BridgeConn 3D motion captures.
   - *Example*: `"water"`, `"sitting"`, `"nature"`.
   - **Crucial Rule**: The system **never silently substitutes** an unrelated sign.

---

## 7. iSign → SMPL-X Status: Boundary & Technical Reality

### Why Continuous iSign Pose → SMPL-X Is Not Yet Claimed
- **Sensor Representation**: iSign pose files use 75 MediaPipe Holistic keypoints (33 body + 21 left hand + 21 right hand) normalized relative to the nose-to-shoulder 2D distance.
- **Lack of Metric Scale**: Unlike BridgeConn, which possesses calibrated metric offsets, iSign YouTube clips lack camera intrinsics and metric depth.
- **Occlusion in Continuous Signing**: In natural broadcast signing, hand-over-hand crossings often result in zero-confidence hand detections.
- **Engineering Verdict**: Naively running the corrected BridgeConn retargeter on uncalibrated 75-point 2D-normalized keypoints would re-introduce jitter and distortion.
- **SignAura Policy**: iSign serves as a **benchmark reference layer**. Actual 3D mesh animation is rendered via BridgeConn only when 100% of required component signs exist. When signs are missing, animation is truthfully withheld rather than faked.

---

## 8. API Endpoints Added

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/isign/status` | Reports dataset directory presence, CSV sizes, archive statuses, and CC license. |
| `GET` | `/api/isign/search/{query}?limit=10` | Fuzzy searches iSign benchmark sentences and returns ranked matching items. |
| `GET` | `/api/isign/item/{uid}` | Exact lookup of a benchmark record by UID with local file availability (`.pose`, `.mp4`). |
| `POST` | `/api/isign/match` | Accepts `{"text": "..."}`, searches iSign, evaluates BridgeConn mapping, and determines animation feasibility. |

---

## 9. Known Limitations

1. **Gated Access**: The full multi-part archives (`iSign-poses_v1.1_part_aa..ad`) require an authorized Hugging Face token with accepted terms.
2. **Missing Signs in BridgeConn**: While BridgeConn contains thousands of vocabulary words, many specific nouns and verbs from continuous broadcasts are not yet converted to SMPL-X.
3. **Alignment Heuristics in iSign**: As noted in the iSign paper (Section 6), some sentence boundaries derived from audio pauses or YouTube timestamps have minor temporal overlap with adjacent utterances.

---

## 10. What Is NOT Implemented Yet

1. **Direct continuous iSign pose-to-SMPL-X kinematic converter**: Converting raw 75-point normalized MediaPipe tracks directly into SMPL-X parameter arrays (`global_orient`, `body_pose`, `left_hand_pose`, `right_hand_pose`, `transl`).
2. **Automated mass-downloader**: We deliberately do not automate downloading the 228 GB multi-part binary archives to respect bandwidth and disk constraints.
3. **Facial blendshape retargeting**: iSign keypoints exclude face mesh, so avatar facial expressions currently default to neutral.
