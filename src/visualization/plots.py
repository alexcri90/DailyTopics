import os
import json
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("Plotly not available. Install with: pip install plotly")

try:
    import matplotlib.pyplot as plt
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False
    logger.warning("WordCloud not available. Install with: pip install wordcloud matplotlib")

def load_topic_data(date_str, algorithm='lda', topics_dir='data/topics'):
    """Load topic data for a specific date"""
    # Search for matching file
    path = Path(topics_dir)
    pattern = f"topics_{date_str}_{algorithm}.json"
    
    for file in path.glob(pattern):
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    logger.warning(f"No topic data found for date {date_str} with algorithm {algorithm}")
    return None

def create_topic_heatmap(topics_data, output_file=None):
    """Create a heatmap of topics across newspapers"""
    if not PLOTLY_AVAILABLE:
        logger.error("Plotly is required for creating heatmaps")
        return None
    
    # Extract data
    topics = topics_data.get('topics', [])
    if not topics:
        logger.error("No topics found in data")
        return None
    
    # Collect all newspapers
    newspapers = set()
    for topic in topics:
        newspapers.update(topic.get('newspaper_weights', {}).keys())
    
    newspapers = list(newspapers)
    topic_labels = [f"Topic {t['topic_id']}: {', '.join(t['words'][:3])}" for t in topics]
    
    # Create matrix of topic weights per newspaper
    heatmap_data = []
    for newspaper in newspapers:
        newspaper_weights = []
        for topic in topics:
            # Get weight of this topic in this newspaper
            weight = topic.get('newspaper_weights', {}).get(newspaper, 0)
            newspaper_weights.append(weight)
        heatmap_data.append(newspaper_weights)
    
    # Transpose data for correct orientation
    heatmap_data_transposed = list(map(list, zip(*heatmap_data)))
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data_transposed,
        x=newspapers,
        y=topic_labels,
        colorscale='Viridis',
        hoverongaps=False))
    
    fig.update_layout(
        title=f"Topic Distribution Across Italian Newspapers ({topics_data.get('date', 'Unknown date')})",
        xaxis_title='Newspaper',
        yaxis_title='Topic',
        height=800,
        width=1200
    )
    
    # Save to file if requested
    if output_file:
        fig.write_html(output_file)
        logger.info(f"Saved heatmap to {output_file}")
    
    return fig

def generate_topic_wordclouds(topics_data, output_dir=None):
    """Generate wordclouds for each topic"""
    if not WORDCLOUD_AVAILABLE:
        logger.error("WordCloud is required for creating wordclouds")
        return None
    
    # Extract topics
    topics = topics_data.get('topics', [])
    if not topics:
        logger.error("No topics found in data")
        return None
    
    wordclouds = {}
    
    for topic in topics:
        # Create dictionary of word:weight
        word_weights = dict(zip(topic.get('words', []), topic.get('weights', [])))
        
        if not word_weights:
            continue
        
        # Generate wordcloud
        wc = WordCloud(
            background_color='white',
            max_words=50,
            contour_width=1,
            contour_color='steelblue',
            width=800,
            height=400
        ).generate_from_frequencies(word_weights)
        
        wordclouds[topic['topic_id']] = wc
        
        # Save to file if requested
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            topic_id = topic['topic_id']
            date = topics_data.get('date', 'unknown')
            filename = f"{output_dir}/wordcloud_{date}_topic_{topic_id}.png"
            
            plt.figure(figsize=(10, 5))
            plt.imshow(wc, interpolation='bilinear')
            plt.axis("off")
            plt.tight_layout(pad=0)
            plt.savefig(filename, dpi=300)
            plt.close()
            
            logger.info(f"Saved wordcloud for topic {topic_id} to {filename}")
    
    return wordclouds

def create_topic_timeline(topic_trends, output_file=None):
    """Create a line chart of topic evolution over time"""
    if not PLOTLY_AVAILABLE:
        logger.error("Plotly is required for creating timelines")
        return None
    
    # Extract dates and topics
    dates = sorted(topic_trends.keys())
    all_topics = {}
    
    # Collect all topics across all dates
    for date, data in topic_trends.items():
        for topic in data.get('topics', []):
            topic_id = f"Topic {topic['topic_id']}: {', '.join(topic['words'][:3])}"
            if topic_id not in all_topics:
                all_topics[topic_id] = {date: 0 for date in dates}
            
            # Calculate topic weight (number of articles)
            weight = len(topic.get('articles', []))
            all_topics[topic_id][date] = weight
    
    # Create figure
    fig = go.Figure()
    
    # Add a line for each topic
    for topic_id, weights_by_date in all_topics.items():
        fig.add_trace(go.Scatter(
            x=dates,
            y=[weights_by_date[date] for date in dates],
            mode='lines+markers',
            name=topic_id
        ))
    
    fig.update_layout(
        title='Topic Evolution Over Time',
        xaxis_title='Date',
        yaxis_title='Number of Articles',
        legend_title='Topics',
        height=600,
        width=1000
    )
    
    # Save to file if requested
    if output_file:
        fig.write_html(output_file)
        logger.info(f"Saved timeline to {output_file}")
    
    return fig

def generate_visualizations(date_str, output_dir='data/visualizations', algorithm='lda'):
    """Generate all visualizations for a specific date"""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load topic data
    topic_data = load_topic_data(date_str, algorithm)
    if not topic_data:
        return None
    
    # Create heatmap
    heatmap_file = f"{output_dir}/heatmap_{date_str}.html"
    create_topic_heatmap(topic_data, output_file=heatmap_file)
    
    # Create wordclouds
    wordcloud_dir = f"{output_dir}/wordclouds"
    generate_topic_wordclouds(topic_data, output_dir=wordcloud_dir)
    
    return {
        'heatmap': heatmap_file,
        'wordcloud_dir': wordcloud_dir
    }

if __name__ == "__main__":
    # Test the module with sample data
    sample_topics_data = {
        'date': '2023-05-15',
        'algorithm': 'lda',
        'num_articles': 100,
        'num_topics': 5,
        'topics': [
            {
                'topic_id': 0,
                'words': ['governo', 'politica', 'ministro', 'presidente', 'parlamento'],
                'weights': [0.1, 0.08, 0.07, 0.06, 0.05],
                'newspaper_weights': {
                    'Il Post': 0.3,
                    'La Repubblica': 0.25,
                    'Corriere della Sera': 0.2,
                    'Il Sole 24 Ore': 0.15
                }
            },
            {
                'topic_id': 1,
                'words': ['calcio', 'squadra', 'campionato', 'partita', 'serie'],
                'weights': [0.12, 0.1, 0.08, 0.06, 0.04],
                'newspaper_weights': {
                    'Gazzetta dello Sport': 0.5,
                    'Corriere della Sera': 0.2,
                    'La Repubblica': 0.1,
                    'Il Post': 0.05
                }
            }
        ]
    }
    
    # Test visualization functions
    if PLOTLY_AVAILABLE:
        heatmap = create_topic_heatmap(sample_topics_data)
        print("Created sample heatmap")
    
    if WORDCLOUD_AVAILABLE:
        wordclouds = generate_topic_wordclouds(sample_topics_data)
        print("Created sample wordclouds")
