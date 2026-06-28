import os
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any

class RAGRetriever:
    def __init__(self, kb_dir: str = "docs"):
        self.kb_dir = kb_dir
        self.chunks = []
        self.chunk_sources = []
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.load_and_chunk_documents()
        if self.chunks:
            self.tfidf_matrix = self.vectorizer.fit_transform(self.chunks)
        else:
            self.tfidf_matrix = None

    def load_and_chunk_documents(self):
        if not os.path.exists(self.kb_dir):
            print(f"Warning: Knowledge base directory '{self.kb_dir}' does not exist.")
            return
        
        for filename in os.listdir(self.kb_dir):
            if filename.endswith(".txt"):
                filepath = os.path.join(self.kb_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Split content into logical paragraphs (double newlines)
                paragraphs = re.split(r'\n\s*\n', content)
                for para in paragraphs:
                    para_clean = para.strip()
                    if para_clean and len(para_clean) > 20:
                        # Append source document context
                        self.chunks.append(para_clean)
                        self.chunk_sources.append(filename)
        
        print(f"RAG: Loaded {len(self.chunks)} chunks from knowledge base.")

    def retrieve(self, query: str, top_k: int = 2) -> str:
        if not self.chunks or self.tfidf_matrix is None:
            return "No documents found in knowledge base."
        
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Get top indices matching query
        top_indices = np.argsort(similarities)[::-1]
        
        results = []
        for idx in top_indices[:top_k]:
            score = similarities[idx]
            if score > 0.02:  # Low threshold to capture any relevant match
                results.append(f"[Source File: {self.chunk_sources[idx]}]\n{self.chunks[idx]}")
        
        if not results:
            return "No specific details found in company policies or technical manual. Rely on general guidelines."
            
        return "\n\n---\n\n".join(results)
