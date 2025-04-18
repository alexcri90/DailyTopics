import re
import unicodedata
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import spaCy and NLTK for natural language processing
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not available. Install with: pip install spacy")
    logger.warning("Then download the Italian model: python -m spacy download it_core_news_sm")

try:
    import nltk
    from nltk.corpus import stopwords
    NLTK_AVAILABLE = True
    
    # Download stopwords if not available
    try:
        stopwords.words('italian')
    except LookupError:
        nltk.download('stopwords')
except ImportError:
    NLTK_AVAILABLE = False
    logger.warning("NLTK not available. Install with: pip install nltk")

# Custom Italian stopwords for newspapers
CUSTOM_STOPWORDS = {
    'leggi', 'articolo', 'continua', 'clicca', 'cookie', 
    'privacy', 'pubblicità', 'condividi', 'abbonati', 'youtube', 
    'twitter', 'facebook', 'instagram'
}

def get_italian_stopwords():
    """Get combined Italian stopwords"""
    if NLTK_AVAILABLE:
        italian_stopwords = set(stopwords.words('italian'))
    else:
        # Fallback to a small set of common Italian stopwords if NLTK is not available
        italian_stopwords = {
            'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 
            'e', 'è', 'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',
            'che', 'chi', 'cui', 'non', 'come', 'dove', 'quando', 'perché',
            'quindi', 'questo', 'questa', 'questi', 'queste', 'quello',
            'quella', 'quelli', 'quelle', 'anche', 'ancora', 'alcuni', 'altre'
        }
    
    # Combine with custom stopwords
    all_stopwords = italian_stopwords.union(CUSTOM_STOPWORDS)
    return all_stopwords

def normalize_text(text):
    """Normalize text (lowercase, remove accents, etc.)"""
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove accents
    text = unicodedata.normalize('NFKD', text)
    text = ''.join([c for c in text if not unicodedata.combining(c)])
    
    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', ' ', text)
    
    # Remove non-word characters
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def preprocess_text_basic(text):
    """Simple preprocessing without NLP libraries"""
    if not text:
        return ""
    
    # Normalize text
    text = normalize_text(text)
    
    # Split into tokens
    tokens = text.split()
    
    # Remove stopwords
    stopwords = get_italian_stopwords()
    tokens = [token for token in tokens if token not in stopwords and len(token) > 2]
    
    return " ".join(tokens)

def preprocess_text_spacy(text):
    """Advanced preprocessing with spaCy"""
    if not SPACY_AVAILABLE:
        logger.warning("spaCy not available, falling back to basic preprocessing")
        return preprocess_text_basic(text)
    
    if not text:
        return ""
    
    try:
        # Load Italian language model
        nlp = spacy.load('it_core_news_sm')
        
        # Process text
        doc = nlp(text)
        
        # Get stopwords
        all_stopwords = get_italian_stopwords()
        
        # Extract lemmatized tokens, excluding stopwords and punctuation
        lemmatized_tokens = [token.lemma_ for token in doc 
                            if token.text not in all_stopwords 
                            and not token.is_punct
                            and not token.is_space
                            and len(token.text) > 2]
        
        return " ".join(lemmatized_tokens)
    except Exception as e:
        logger.error(f"Error in spaCy preprocessing: {e}")
        logger.info("Falling back to basic preprocessing")
        return preprocess_text_basic(text)

def preprocess_article(article):
    """Preprocess an article dictionary"""
    # Combine title, summary, and content
    text_parts = []
    
    if 'title' in article and article['title']:
        text_parts.append(article['title'])
    
    if 'kicker' in article and article['kicker']:
        text_parts.append(article['kicker'])
        
    if 'summary' in article and article['summary']:
        text_parts.append(article['summary'])
    
    if 'content' in article and article['content']:
        text_parts.append(article['content'])
    
    combined_text = ' '.join(text_parts)
    
    # Use spaCy if available, otherwise use basic preprocessing
    if SPACY_AVAILABLE:
        return preprocess_text_spacy(combined_text)
    else:
        return preprocess_text_basic(combined_text)

def preprocess_articles(articles):
    """Preprocess a list of articles"""
    preprocessed_articles = []
    
    for article in articles:
        article_copy = article.copy()
        article_copy['preprocessed_text'] = preprocess_article(article)
        preprocessed_articles.append(article_copy)
    
    return preprocessed_articles

if __name__ == "__main__":
    # Test the module
    test_text = """
    L'Italia è un paese dell'Europa meridionale. La capitale è Roma. 
    Il Presidente della Repubblica è Sergio Mattarella.
    Visita il nostro sito web: https://www.example.com o contattaci a info@example.com.
    """
    
    print("Original text:")
    print(test_text)
    print("\nBasic preprocessing:")
    print(preprocess_text_basic(test_text))
    
    if SPACY_AVAILABLE:
        print("\nspaCy preprocessing:")
        print(preprocess_text_spacy(test_text))
