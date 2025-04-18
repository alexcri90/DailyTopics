#!/usr/bin/env python3
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.collect import collect_rss_feeds, extract_full_content
from src.data.database import store_articles

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting news collection process")
    
    # Create data directories if they don't exist
    os.makedirs('data/raw', exist_ok=True)
    
    # Collect articles from RSS feeds
    articles = collect_rss_feeds()
    logger.info(f"Collected {len(articles)} articles from RSS feeds")
    
    # Extract full content for a subset (can be adjusted)
    max_articles = int(os.environ.get('MAX_ARTICLES', '50'))
    articles_with_content = extract_full_content(articles, max_articles=max_articles)
    
    # Store in database
    storage_type = os.environ.get('STORAGE_TYPE', 'sqlite')
    inserted_count = store_articles(articles_with_content, storage=storage_type)
    logger.info(f"Stored {inserted_count} articles in {storage_type} database")
    
    # Save raw data as backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_file = f"data/raw/articles_{timestamp}.json"
    
    import json
    with open(raw_file, 'w', encoding='utf-8') as f:
        # Handle datetime objects for JSON serialization
        json.dump(articles_with_content, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"Saved raw data to {raw_file}")
    logger.info("News collection process completed")

if __name__ == "__main__":
    main()
