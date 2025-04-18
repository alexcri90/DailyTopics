import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from src.visualization.plots import load_topic_data, create_topic_heatmap, generate_topic_wordclouds
from src.data.database import get_articles_by_date

# Set page config
st.set_page_config(
    page_title="Italian News Topics",
    page_icon="í³°",
    layout="wide",
    initial_sidebar_state="expanded",
)

def get_available_dates():
    """Get dates with available topic data"""
    topics_dir = Path('data/topics')
    
    if not topics_dir.exists():
        return []
    
    # Find all topic files
    files = list(topics_dir.glob('topics_*.json'))
    
    # Extract dates from filenames
    dates = []
    for file in files:
        # Filename format: topics_YYYY-MM-DD_algorithm.json
        parts = file.name.split('_')
        if len(parts) >= 2:
            date_str = parts[1]
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
                dates.append(date.strftime('%Y-%m-%d'))
            except ValueError:
                continue
    
    return sorted(set(dates), reverse=True)

def main():
    st.title("Italian News Topic Visualization")
    
    st.sidebar.header("Options")
    
    # Get available dates
    available_dates = get_available_dates()
    
    if not available_dates:
        st.warning("No topic data available. Please run the data collection and topic modeling scripts first.")
        return
    
    # Date selection
    selected_date = st.sidebar.selectbox(
        "Select date to view topics",
        available_dates
    )
    
    # Algorithm selection
    algorithm = st.sidebar.selectbox(
        "Select topic modeling algorithm",
        ["lda", "nmf", "bertopic"],
        index=0
    )
    
    # Load data for selected date and algorithm
    topic_data = load_topic_data(selected_date, algorithm)
    
    if not topic_data:
        st.error(f"No topic data available for {selected_date} with algorithm {algorithm}")
        return
    
    # Display basic information
    st.write(f"Date: {selected_date}")
    st.write(f"Algorithm: {algorithm.upper()}")
    st.write(f"Number of articles: {topic_data.get('num_articles', 0)}")
    st.write(f"Number of topics: {topic_data.get('num_topics', 0)}")
    
    # Create tabs for different visualizations
    tab1, tab2, tab3 = st.tabs(["Topic Heatmap", "Topic Details", "Articles"])
    
    with tab1:
        st.header("Topic Heatmap")
        fig = create_topic_heatmap(topic_data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Failed to create heatmap")
    
    with tab2:
        st.header("Topic Details")
        
        # Topic selection
        topics = topic_data.get('topics', [])
        topic_options = [f"Topic {t['topic_id']}: {', '.join(t['words'][:3])}" for t in topics]
        
        selected_topic_idx = st.selectbox(
            "Select a topic to view details",
            range(len(topic_options)),
            format_func=lambda i: topic_options[i]
        )
        
        # Display selected topic details
        if topics and selected_topic_idx < len(topics):
            topic = topics[selected_topic_idx]
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Top Words")
                
                # Create word list with weights
                word_list = zip(topic.get('words', []), topic.get('weights', []))
                for word, weight in word_list:
                    st.write(f"- {word}: {weight:.4f}")
            
            with col2:
                st.subheader("Word Cloud")
                # Generate word cloud
                wordcloud = generate_topic_wordclouds({
                    'topics': [topic]
                })
                
                if wordcloud and topic['topic_id'] in wordcloud:
                    wc = wordcloud[topic['topic_id']]
                    st.image(wc.to_array())
    
    with tab3:
        st.header("Articles by Topic")
        
        # Topic selection for articles
        topics = topic_data.get('topics', [])
        topic_options = [f"Topic {t['topic_id']}: {', '.join(t['words'][:3])}" for t in topics]
        
        selected_topic_idx = st.selectbox(
            "Select a topic to view articles",
            range(len(topic_options)),
            format_func=lambda i: topic_options[i],
            key="articles_topic_selector"
        )
        
        # Display articles for selected topic
        if topics and selected_topic_idx < len(topics):
            topic = topics[selected_topic_idx]
            articles = topic.get('articles', [])
            
            if not articles:
                st.info("No articles found for this topic")
            else:
                st.write(f"Found {len(articles)} articles for this topic")
                
                for article in articles:
                    with st.expander(f"{article.get('title')} - {article.get('newspaper')}"):
                        st.write(article.get('summary', 'No summary available'))
                        st.markdown(f"[Read full article]({article.get('url', '#')})")

if __name__ == "__main__":
    main()
