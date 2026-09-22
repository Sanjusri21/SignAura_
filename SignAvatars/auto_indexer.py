"""
Automated continuous indexer for BridgeConn shards.
Monitors shard downloads in D:\\SignAuraData\\BridgeConn\\shards.
Indexes shards as soon as they complete download.
Exits when all 7 shards are fully indexed.
"""

import os
import sys
import time
import json
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ingest_bridgeconn_dataset import index_all_available_shards, SHARD_SIZES, is_shard_complete

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [AUTO-INDEX] %(message)s")
logger = logging.getLogger("AutoIndexer")

def main():
    logger.info("Starting Auto-Indexer daemon for all 7 shards...")
    total_target_shards = len(SHARD_SIZES)
    
    while True:
        stats = index_all_available_shards()
        total_samples = stats.get("total_samples", 0)
        unique_glosses = stats.get("unique_dataset_glosses", 0)
        
        # Check how many shards are complete
        completed_shards = [s for s in SHARD_SIZES if is_shard_complete(s)]
        logger.info(f"Progress: {len(completed_shards)}/{total_target_shards} shards completed. Indexed samples: {total_samples}, Unique glosses: {unique_glosses}")
        
        if len(completed_shards) == total_target_shards and total_samples >= 3000:
            logger.info("ALL 7 SHARDS FULLY DOWNLOADED AND INDEXED!")
            break
            
        time.sleep(20)

if __name__ == "__main__":
    main()
