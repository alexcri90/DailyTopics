#!/usr/bin/env python3
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.database import get_articles_by_date
from src.models.preprocess import preprocess_articles
from src.models.topic_model import process_articles_for_topics, save_topic_results

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_single_day(date_str, algorithm='lda', n_topics=10, storage='sqlite'):
    """Process topics for a single day"""
    # Get articles for the specified date
    articles = get_articles_by_date(date_str, storage=storage)
    
    if not articles:
        logger.warning(f"No articles found for date {date_str}")
        return None
    
    logger.info(f"Processing {len(articles)} articles for date {date_str}")
    
    # Preprocess articles
    preprocessed_articles = preprocess_articles(articles)
    
    # Process topics
    topic_results = process_articles_for_topics(
        preprocessed_articles,
        algorithm=algorithm,
        n_topics=n_topics
    )
    
    if topic_results:
        # Save results
        save_topic_results(topic_results)
        return topic_results
    else:
        logger.error(f"Failed to process topics for {date_str}")
        return None

def process_date_range(start_date, end_date, algorithm='lda', n_topics=10, storage='sqlite'):
    """Process topics for a range of dates"""
    current_date = start_date
    results = {}
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        logger.info(f"Processing date: {date_str}")
        
        # Process topics for the current date
        topic_results = process_single_day(
            date_str, 
            algorithm=algorithm,
            n_topics=n_topics,
            storage=storage
        )
        
        if topic_results:
            results[date_str] = topic_results
        
        # Move to the next day
        current_date += timedelta(days=1)
    
    return results

def main():
    """Main function to process topics"""
    logger.info("Starting topic processing")
    
    # Create directories if they don't exist
    os.makedirs('data/topics', exist_ok=True)
    
    # Get parameters from environment variables or use defaults
    algorithm = os.environ.get('TOPIC_ALGORITHM', 'lda')
    n_topics = int(os.environ.get('NUM_TOPICS', '10'))
    storage_type = os.environ.get('STORAGE_TYPE', 'sqlite')
    
    # Process the last 10 days by default
    end_date = datetime.now()
    start_date = end_date - timedelta(days=10)
    
    # Process topics for the date range
    results = process_date_range(
        start_date,
        end_date,
        algorithm=algorithm,
        n_topics=n_topics,
        storage=storage_type
    )
    
    # Save summary
    summary_file = f"data/topics/summary_{datetime.now().strftime('%Y%m%d')}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        # Just save date and number of topics found
        summary = {
            date_str: {
                'num_topics': result.get('num_topics', 0),
                'num_articles': result.get('num_articles', 0)
            }
            for date_str, result in results.items()
        }
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved summary to {summary_file}")
    logger.info("Topic processing completed")

if __name__ == "__main__":
    main()
