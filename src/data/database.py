import os
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# Try to import MongoDB if available
try:
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Local SQLite database for development
def get_sqlite_connection():
    """Get connection to SQLite database"""
    db_path = Path('data/italian_news.db')
    os.makedirs(db_path.parent, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    
    # Create tables if they don't exist
    with conn:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            newspaper TEXT,
            title TEXT,
            kicker TEXT,
            summary TEXT,
            content TEXT,
            url TEXT,
            published_date TEXT,
            collection_date TEXT,
            language TEXT,
            authors TEXT,
            categories TEXT
        )
        ''')
        
        conn.execute('''
        CREATE TABLE IF NOT EXISTS topics (
            id TEXT PRIMARY KEY,
            date TEXT,
            topic_id INTEGER,
            topic_words TEXT,
            topic_weight REAL,
            topic_articles TEXT
        )
        ''')
    
    return conn

def store_articles_sqlite(articles_data):
    """Store articles in SQLite database"""
    conn = get_sqlite_connection()
    
    inserted_count = 0
    for article in articles_data:
        try:
            with conn:
                # Convert lists to JSON strings
                article_copy = article.copy()
                if 'authors' in article_copy and isinstance(article_copy['authors'], list):
                    article_copy['authors'] = json.dumps(article_copy['authors'])
                if 'categories' in article_copy and isinstance(article_copy['categories'], list):
                    article_copy['categories'] = json.dumps(article_copy['categories'])
                
                conn.execute('''
                INSERT OR REPLACE INTO articles 
                (id, newspaper, title, kicker, summary, content, url, 
                published_date, collection_date, language, authors, categories)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article_copy['article_id'],
                    article_copy['newspaper'],
                    article_copy['title'],
                    article_copy.get('kicker', ''),
                    article_copy.get('summary', ''),
                    article_copy.get('content', ''),
                    article_copy['url'],
                    article_copy['published_date'],
                    article_copy['collection_date'],
                    article_copy.get('language', 'it'),
                    article_copy.get('authors', '[]'),
                    article_copy.get('categories', '[]')
                ))
                inserted_count += 1
        except Exception as e:
            logger.error(f"Error inserting article {article.get('article_id')}: {e}")
    
    conn.close()
    return inserted_count

# MongoDB for production if available
def get_mongodb_connection():
    """Get connection to MongoDB database"""
    if not MONGODB_AVAILABLE:
        logger.warning("PyMongo is not available. Install with: pip install pymongo")
        return None
    
    # Use environment variable or default to localhost
    connection_string = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    try:
        client = MongoClient(connection_string)
        db = client['italian_news_topics']
        return db
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        return None

def store_articles_mongodb(articles_data):
    """Store articles in MongoDB database"""
    db = get_mongodb_connection()
    if not db:
        logger.error("MongoDB connection failed, falling back to SQLite")
        return store_articles_sqlite(articles_data)
    
    try:
        articles_collection = db['articles']
        
        # Create index on published_date if it doesn't exist
        articles_collection.create_index('published_date')
        
        # Insert articles
        result = articles_collection.insert_many(articles_data)
        return len(result.inserted_ids)
    except Exception as e:
        logger.error(f"Error storing articles in MongoDB: {e}")
        logger.info("Falling back to SQLite")
        return store_articles_sqlite(articles_data)

def store_articles(articles_data, storage='sqlite'):
    """Store articles in database"""
    if storage == 'mongodb' and MONGODB_AVAILABLE:
        return store_articles_mongodb(articles_data)
    else:
        return store_articles_sqlite(articles_data)

def get_articles_by_date(date, storage='sqlite'):
    """Get articles by date"""
    if isinstance(date, datetime):
        date_str = date.strftime("%Y-%m-%d")
    else:
        date_str = date
    
    if storage == 'mongodb' and MONGODB_AVAILABLE:
        db = get_mongodb_connection()
        if not db:
            logger.warning("MongoDB connection failed, falling back to SQLite")
            return get_articles_by_date(date, storage='sqlite')
        
        articles_collection = db['articles']
        # Query for articles published on the given date
        articles = list(articles_collection.find({
            'published_date': {'': f'^{date_str}'}
        }))
        return articles
    else:
        conn = get_sqlite_connection()
        cursor = conn.execute('''
        SELECT * FROM articles 
        WHERE published_date LIKE ?
        ''', (f'{date_str}%',))
        
        columns = [column[0] for column in cursor.description]
        articles = []
        
        for row in cursor.fetchall():
            article = dict(zip(columns, row))
            
            # Convert JSON strings back to lists
            if 'authors' in article:
                try:
                    article['authors'] = json.loads(article['authors'])
                except:
                    article['authors'] = []
            
            if 'categories' in article:
                try:
                    article['categories'] = json.loads(article['categories'])
                except:
                    article['categories'] = []
            
            articles.append(article)
        
        conn.close()
        return articles

if __name__ == "__main__":
    # Test the module
    test_article = {
        'article_id': 'test-article-id',
        'newspaper': 'Test Newspaper',
        'title': 'Test Article',
        'summary': 'This is a test article summary',
        'url': 'https://example.com/test-article',
        'published_date': datetime.now().isoformat(),
        'collection_date': datetime.now().isoformat(),
        'language': 'it',
        'authors': ['Test Author'],
        'categories': ['Test', 'Demo']
    }
    
    # Test SQLite storage
    inserted = store_articles([test_article], storage='sqlite')
    print(f"Inserted {inserted} article(s) into SQLite")
    
    # Test retrieval
    today = datetime.now().strftime("%Y-%m-%d")
    articles = get_articles_by_date(today, storage='sqlite')
    print(f"Retrieved {len(articles)} article(s) from SQLite")
