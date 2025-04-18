import feedparser
import time
import uuid
from datetime import datetime
from newspaper import Article
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dictionary of newspaper RSS feeds
NEWSPAPER_FEEDS = {
    'Il Post': 'https://www.ilpost.it/feed/',
    'Il Tempo': 'https://www.iltempo.it/rss.jsp',
    'La Repubblica': 'https://www.repubblica.it/rss/homepage/rss2.0.xml',
    'Corriere della Sera': 'https://xml2.corriereobjects.it/rss/homepage.xml',
    'Il Sole 24 Ore': 'https://www.ilsole24ore.com/rss/italia.xml',
    'La Stampa': 'https://www.lastampa.it/rss.xml',
    'Il Messaggero': 'https://www.ilmessaggero.it/rss/home.xml',
    'Il Fatto Quotidiano': 'https://www.ilfattoquotidiano.it/feed/',
    'Avvenire': 'https://www.avvenire.it/rss',
    'Il Giornale': 'https://www.ilgiornale.it/feed.xml',
    'Libero': 'https://www.liberoquotidiano.it/rss/italia.rss',
    'Il Mattino': 'https://www.ilmattino.it/rss/primopiano.xml',
    'L\'Unità': 'http://www.unita.it/rss',
    'Il Foglio': 'https://www.ilfoglio.it/rss/sezione/1131/',
}

def collect_rss_feeds():
    """Collect articles from RSS feeds of Italian newspapers"""
    logger.info("Starting RSS feed collection")
    articles_data = []
    
    for newspaper, feed_url in NEWSPAPER_FEEDS.items():
        try:
            logger.info(f"Collecting from {newspaper}")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries:
                article = {
                    'article_id': str(uuid.uuid4()),
                    'newspaper': newspaper,
                    'title': entry.title,
                    'summary': entry.summary if 'summary' in entry else '',
                    'url': entry.link,
                    'published_date': entry.published if 'published' in entry else datetime.now().isoformat(),
                    'collection_date': datetime.now().isoformat(),
                    'language': 'it',
                    'authors': entry.get('authors', []),
                    'categories': entry.get('tags', []),
                }
                articles_data.append(article)
                
            logger.info(f"Collected {len(feed.entries)} articles from {newspaper}")
        except Exception as e:
            logger.error(f"Error collecting from {newspaper}: {e}")
    
    logger.info(f"Total articles collected: {len(articles_data)}")
    return articles_data

def extract_full_content(articles_data, max_articles=None, delay=2):
    """Extract full content from article URLs using Newspaper3k"""
    logger.info("Starting full content extraction")
    
    # Limit number of articles if specified
    if max_articles and len(articles_data) > max_articles:
        articles_to_process = articles_data[:max_articles]
        logger.info(f"Processing {max_articles} out of {len(articles_data)} articles")
    else:
        articles_to_process = articles_data
    
    for i, article_data in enumerate(articles_to_process):
        try:
            logger.info(f"Processing article {i+1}/{len(articles_to_process)}: {article_data['title']}")
            
            # Download and parse article
            article = Article(article_data['url'], language='it')
            article.download()
            time.sleep(delay)  # Be respectful with requests
            article.parse()
            
            # Update article data with full content
            article_data['content'] = article.text
            article_data['kicker'] = getattr(article, 'meta_data', {}).get('description', '')
            
            # Update authors if available
            if article.authors:
                article_data['authors'] = article.authors
                
            # Update publish date if available
            if article.publish_date:
                article_data['published_date'] = article.publish_date.isoformat()
                
        except Exception as e:
            logger.error(f"Error processing {article_data['url']}: {e}")
    
    logger.info("Content extraction completed")
    return articles_data

if __name__ == "__main__":
    # Test the module
    articles = collect_rss_feeds()
    articles_with_content = extract_full_content(articles, max_articles=5)
    
    # Print sample result
    if articles_with_content:
        sample = articles_with_content[0]
        print(f"Sample article: {sample['title']} from {sample['newspaper']}")
        print(f"Content length: {len(sample.get('content', ''))}")
