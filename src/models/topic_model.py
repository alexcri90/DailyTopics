import os
import json
import numpy as np
import logging
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import topic modeling libraries
try:
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.decomposition import LatentDirichletAllocation, NMF
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available. Install with: pip install scikit-learn")

try:
    import gensim
    from gensim.corpora import Dictionary
    from gensim.models import LdaModel
    GENSIM_AVAILABLE = True
except ImportError:
    GENSIM_AVAILABLE = False
    logger.warning("gensim not available. Install with: pip install gensim")

try:
    from bertopic import BERTopic
    BERTOPIC_AVAILABLE = True
except ImportError:
    BERTOPIC_AVAILABLE = False
    logger.warning("BERTopic not available. Install with: pip install bertopic")

def perform_lda_sklearn(preprocessed_texts, n_topics=10):
    """Perform Latent Dirichlet Allocation using scikit-learn"""
    if not SKLEARN_AVAILABLE:
        logger.error("scikit-learn is required for LDA")
        return None, None
    
    logger.info(f"Performing LDA with {n_topics} topics")
    
    # Create document-term matrix
    vectorizer = CountVectorizer(max_df=0.95, min_df=2)
    dtm = vectorizer.fit_transform(preprocessed_texts)
    
    # Fit LDA model
    lda_model = LatentDirichletAllocation(
        n_components=n_topics, 
        random_state=42,
        learning_method='online'
    )
    lda_model.fit(dtm)
    
    # Get feature names (words)
    feature_names = vectorizer.get_feature_names_out()
    
    # Extract topics
    topics = []
    for topic_idx, topic in enumerate(lda_model.components_):
        top_words_idx = topic.argsort()[:-11:-1]  # Get top 10 words
        top_words = [feature_names[i] for i in top_words_idx]
        topics.append({
            'topic_id': topic_idx,
            'words': top_words,
            'weights': topic[top_words_idx].tolist()
        })
    
    # Get document-topic distributions
    doc_topic_dists = lda_model.transform(dtm)
    
    return topics, doc_topic_dists, vectorizer, lda_model

def perform_nmf(preprocessed_texts, n_topics=10):
    """Perform Non-negative Matrix Factorization"""
    if not SKLEARN_AVAILABLE:
        logger.error("scikit-learn is required for NMF")
        return None, None
    
    logger.info(f"Performing NMF with {n_topics} topics")
    
    # Create TF-IDF matrix
    vectorizer = TfidfVectorizer(max_df=0.95, min_df=2)
    tfidf = vectorizer.fit_transform(preprocessed_texts)
    
    # Fit NMF model
    nmf_model = NMF(
        n_components=n_topics, 
        random_state=42,
        alpha=.1,
        l1_ratio=.5
    )
    nmf_model.fit(tfidf)
    
    # Get feature names (words)
    feature_names = vectorizer.get_feature_names_out()
    
    # Extract topics
    topics = []
    for topic_idx, topic in enumerate(nmf_model.components_):
        top_words_idx = topic.argsort()[:-11:-1]  # Get top 10 words
        top_words = [feature_names[i] for i in top_words_idx]
        topics.append({
            'topic_id': topic_idx,
            'words': top_words,
            'weights': topic[top_words_idx].tolist()
        })
    
    # Get document-topic distributions
    doc_topic_dists = nmf_model.transform(tfidf)
    
    return topics, doc_topic_dists, vectorizer, nmf_model

def try_bertopic(preprocessed_texts):
    """Try using BERTopic if available"""
    if not BERTOPIC_AVAILABLE:
        logger.error("BERTopic is not available")
        return None, None
    
    try:
        logger.info("Performing topic modeling with BERTopic")
        
        # Initialize BERTopic model with Italian model
        from sklearn.feature_extraction.text import CountVectorizer
        vectorizer = CountVectorizer(stop_words="italian")
        topic_model = BERTopic(
            language="italian",
            vectorizer_model=vectorizer,
            nr_topics="auto"
        )
        
        # Fit model and transform documents
        topics, probs = topic_model.fit_transform(preprocessed_texts)
        
        # Extract topic information
        topic_info = topic_model.get_topic_info()
        topic_representations = []
        
        for topic in topic_info.itertuples():
            if topic.Topic != -1:  # Skip outlier topic
                words = [word for word, _ in topic_model.get_topic(topic.Topic)]
                weights = [weight for _, weight in topic_model.get_topic(topic.Topic)]
                topic_representations.append({
                    'topic_id': topic.Topic,
                    'words': words,
                    'weights': weights,
                    'count': topic.Count
                })
        
        return topic_representations, topics, probs, topic_model
    except Exception as e:
        logger.error(f"Error in BERTopic: {e}")
        return None, None, None, None

def generate_topic_label(topic_words):
    """Generate a descriptive label for a topic based on its key words"""
    if not topic_words:
        return "Miscellaneous"
    
    # Simple method: return the most frequent word
    return topic_words[0].capitalize()

def process_articles_for_topics(articles, algorithm='lda', n_topics=10):
    """Process articles and extract topics"""
    preprocessed_texts = [article.get('preprocessed_text', '') for article in articles if article.get('preprocessed_text')]
    
    if not preprocessed_texts:
        logger.error("No preprocessed texts available")
        return None
    
    logger.info(f"Processing {len(preprocessed_texts)} articles for topic modeling")
    
    # Choose algorithm
    if algorithm == 'nmf':
        topics, doc_topic_dists, _, _ = perform_nmf(preprocessed_texts, n_topics)
    elif algorithm == 'bertopic' and BERTOPIC_AVAILABLE:
        topics, _, _, _ = try_bertopic(preprocessed_texts)
        # BERTopic manages its own number of topics
        if topics:
            logger.info(f"BERTopic found {len(topics)} topics")
    else:  # Default to LDA
        topics, doc_topic_dists, _, _ = perform_lda_sklearn(preprocessed_texts, n_topics)
    
    if not topics:
        logger.error("Topic modeling failed")
        return None
    
    # Add labels to topics
    for topic in topics:
        topic['label'] = generate_topic_label(topic['words'])
    
    # Assign topics to articles if doc_topic_dists is available
    if 'doc_topic_dists' in locals() and doc_topic_dists is not None:
        for i, article in enumerate(articles):
            if i < len(doc_topic_dists):
                # Get the dominant topic
                dominant_topic_idx = np.argmax(doc_topic_dists[i])
                article['dominant_topic'] = int(dominant_topic_idx)
                article['topic_distribution'] = doc_topic_dists[i].tolist()
            else:
                article['dominant_topic'] = -1
                article['topic_distribution'] = []
    
    # Group articles by topic
    articles_by_topic = {}
    for topic in topics:
        topic_id = topic['topic_id']
        articles_by_topic[topic_id] = []
    
    for article in articles:
        if 'dominant_topic' in article and article['dominant_topic'] in articles_by_topic:
            topic_id = article['dominant_topic']
            articles_by_topic[topic_id].append({
                'article_id': article.get('article_id', ''),
                'title': article.get('title', ''),
                'newspaper': article.get('newspaper', ''),
                'url': article.get('url', ''),
                'summary': article.get('summary', '')
            })
    
    # Add articles to topics
    for topic in topics:
        topic_id = topic['topic_id']
        if topic_id in articles_by_topic:
            topic['articles'] = articles_by_topic[topic_id]
        else:
            topic['articles'] = []
    
    # Calculate topic proportions by newspaper
    newspapers = list(set(article.get('newspaper', '') for article in articles))
    for topic in topics:
        newspaper_counts = {}
        newspaper_weights = {}
        
        for newspaper in newspapers:
            # Count articles from this newspaper in this topic
            count = sum(1 for article in topic['articles'] if article.get('newspaper') == newspaper)
            newspaper_counts[newspaper] = count
            
            # Calculate proportion
            total_articles_from_newspaper = sum(1 for article in articles if article.get('newspaper') == newspaper)
            if total_articles_from_newspaper > 0:
                weight = count / total_articles_from_newspaper
            else:
                weight = 0
            
            newspaper_weights[newspaper] = weight
        
        topic['newspaper_counts'] = newspaper_counts
        topic['newspaper_weights'] = newspaper_weights
    
    # Add metadata
    result = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'algorithm': algorithm,
        'num_articles': len(articles),
        'num_topics': len(topics),
        'topics': topics
    }
    
    return result

def save_topic_results(topic_results, output_dir='data/topics'):
    """Save topic modeling results to file"""
    os.makedirs(output_dir, exist_ok=True)
    
    date_str = topic_results.get('date', datetime.now().strftime('%Y-%m-%d'))
    algorithm = topic_results.get('algorithm', 'unknown')
    
    filename = f"{output_dir}/topics_{date_str}_{algorithm}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(topic_results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved topic results to {filename}")
    
    return filename

if __name__ == "__main__":
    # Test with sample data
    sample_texts = [
        "Il governo italiano ha approvato la nuova legge finanziaria che prevede importanti riforme fiscali",
        "La squadra di calcio ha vinto il campionato dopo una partita emozionante",
        "Il festival del cinema di Venezia ha premiato il film italiano come miglior opera",
        "Nuove politiche economiche per affrontare l'inflazione crescente in Italia",
        "Il presidente del consiglio ha incontrato i leader europei per discutere delle politiche migratorie",
        "La vittoria della nazionale di pallavolo ha entusiasmato i tifosi italiani",
        "Il nuovo libro dell'autore italiano è in cima alle classifiche di vendita",
        "Il ministro dell'economia ha presentato il piano per la riduzione del debito pubblico",
        "La mostra d'arte contemporanea ha attirato visitatori da tutta Europa",
        "Lo sciopero dei trasporti ha causato disagi in diverse città italiane",
    ]
    
    # Test LDA
    lda_topics, _, _, _ = perform_lda_sklearn(sample_texts, n_topics=3)
    print("\nLDA Topics:")
    for topic in lda_topics:
        print(f"Topic {topic['topic_id']}: {', '.join(topic['words'])}")
    
    # Test NMF
    nmf_topics, _, _, _ = perform_nmf(sample_texts, n_topics=3)
    print("\nNMF Topics:")
    for topic in nmf_topics:
        print(f"Topic {topic['topic_id']}: {', '.join(topic['words'])}")
