from setuptools import setup, find_packages

setup(
    name="dailytopics",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "feedparser",
        "newspaper3k",
        "beautifulsoup4",
        "requests",
        "pandas",
        "numpy",
        "scikit-learn",
        "spacy",
        "nltk",
        "gensim",
        "plotly",
        "matplotlib",
        "wordcloud",
        "networkx",
        "streamlit",
        "pymongo",
    ],
    python_requires=">=3.8",
)
