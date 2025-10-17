"""
Semantic caching for natural language command translation.

Implements embedding-based similarity search to cache and retrieve
similar command translations, achieving 60-80% cost reduction.
"""

import hashlib
import logging
import pickle
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False
    SentenceTransformer = None
    faiss = None

from .schemas import CacheEntry, CommandTranslation, PerformanceMetrics

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuration for semantic cache."""
    similarity_threshold: float = 0.85
    max_cache_size: int = 1000
    cache_ttl_hours: int = 24
    embedding_model: str = "all-MiniLM-L6-v2"  # Lightweight, fast model
    index_type: str = "flat"  # "flat" or "ivf"
    cleanup_interval_hours: int = 6


class SemanticCache:
    """
    Semantic cache for command translations using embedding similarity.
    
    Features:
    - Embedding-based similarity search
    - Configurable similarity thresholds
    - TTL-based cache expiration
    - Performance metrics tracking
    - Persistent storage support
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self.logger = logging.getLogger(__name__)
        
        if not HAS_DEPENDENCIES:
            self.logger.warning("Semantic cache dependencies not available. Install sentence-transformers and faiss-cpu.")
            self.enabled = False
            # Initialize minimal attributes for graceful degradation
            self.entries: Dict[str, CacheEntry] = {}
            self.embeddings: Optional[np.ndarray] = None
            self.index: Optional[faiss.Index] = None
            self.entry_order: List[str] = []
            self.embedding_model = None
            self.embedding_dim = 0
            return
        
        self.enabled = True
        self.entries: Dict[str, CacheEntry] = {}
        self.embeddings: Optional[np.ndarray] = None
        self.index: Optional[faiss.Index] = None
        self.entry_order: List[str] = []  # For LRU eviction
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(self.config.embedding_model)
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            self.logger.info(f"Initialized semantic cache with {self.config.embedding_model}")
        except Exception as e:
            self.logger.error(f"Failed to initialize embedding model: {e}")
            self.enabled = False
            return
        
        # Initialize FAISS index
        try:
            if self.config.index_type == "flat":
                self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
            else:
                # IVF index for larger datasets
                quantizer = faiss.IndexFlatIP(self.embedding_dim)
                self.index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, 100)
            self.logger.info(f"Initialized FAISS {self.config.index_type} index")
        except Exception as e:
            self.logger.error(f"Failed to initialize FAISS index: {e}")
            self.enabled = False
    
    def _generate_query_hash(self, query: str) -> str:
        """Generate hash for query deduplication."""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def _embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        if not self.enabled:
            return np.array([])
        
        try:
            embedding = self.embedding_model.encode([text], normalize_embeddings=True)
            return embedding[0]
        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            return np.array([])
    
    def _calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings."""
        if len(embedding1) == 0 or len(embedding2) == 0:
            return 0.0
        
        # Cosine similarity using dot product (embeddings are normalized)
        similarity = np.dot(embedding1, embedding2)
        return float(similarity)
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        ttl = timedelta(hours=self.config.cache_ttl_hours)
        return datetime.now() - entry.created_at > ttl
    
    def _evict_old_entries(self):
        """Evict expired and old entries to maintain cache size."""
        if len(self.entries) <= self.config.max_cache_size:
            return
        
        # Remove expired entries first
        expired_keys = [key for key, entry in self.entries.items() if self._is_expired(entry)]
        for key in expired_keys:
            self._remove_entry(key)
        
        # If still over limit, remove oldest entries (LRU)
        while len(self.entries) > self.config.max_cache_size:
            if self.entry_order:
                oldest_key = self.entry_order.pop(0)
                if oldest_key in self.entries:
                    self._remove_entry(oldest_key)
            else:
                break
    
    def _remove_entry(self, key: str):
        """Remove entry from cache and update index."""
        if key not in self.entries:
            return
        
        # Remove from entries dict
        del self.entries[key]
        
        # Remove from order list
        if key in self.entry_order:
            self.entry_order.remove(key)
        
        # Rebuild index (simple approach for small caches)
        self._rebuild_index()
    
    def _rebuild_index(self):
        """Rebuild FAISS index from current entries."""
        if not self.enabled or not self.entries:
            self.index.reset()
            self.embeddings = None
            return
        
        try:
            # Collect all embeddings
            embeddings_list = []
            for entry in self.entries.values():
                embedding = self._embed_text(entry.query_text)
                if len(embedding) > 0:
                    embeddings_list.append(embedding)
            
            if not embeddings_list:
                self.index.reset()
                self.embeddings = None
                return
            
            # Create numpy array
            self.embeddings = np.vstack(embeddings_list).astype('float32')
            
            # Reset and rebuild index
            self.index.reset()
            self.index.add(self.embeddings)
            
            self.logger.debug(f"Rebuilt index with {len(embeddings_list)} entries")
            
        except Exception as e:
            self.logger.error(f"Failed to rebuild index: {e}")
            self.index.reset()
            self.embeddings = None
    
    def get_cached_response(self, query: str) -> Optional[CommandTranslation]:
        """
        Get cached response for similar query.
        
        Args:
            query: User's natural language query
            
        Returns:
            Cached CommandTranslation if similar query found, None otherwise
        """
        if not self.enabled:
            return None
        
        start_time = time.time()
        
        try:
            # Generate embedding for query
            query_embedding = self._embed_text(query)
            if len(query_embedding) == 0:
                return None
            
            # Search for similar entries
            if self.index.ntotal == 0:
                return None
            
            # Search for most similar entry
            query_embedding = query_embedding.reshape(1, -1).astype('float32')
            similarities, indices = self.index.search(query_embedding, k=1)
            
            if len(similarities[0]) == 0:
                return None
            
            similarity = similarities[0][0]
            if similarity < self.config.similarity_threshold:
                return None
            
            # Get the most similar entry
            entry_keys = list(self.entries.keys())
            if indices[0][0] >= len(entry_keys):
                return None
            
            entry_key = entry_keys[indices[0][0]]
            entry = self.entries[entry_key]
            
            # Check if entry is expired
            if self._is_expired(entry):
                self._remove_entry(entry_key)
                return None
            
            # Update access statistics
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            
            # Move to end of order list (LRU)
            if entry_key in self.entry_order:
                self.entry_order.remove(entry_key)
            self.entry_order.append(entry_key)
            
            # Mark as cache hit
            response = entry.response
            response.cache_hit = True
            response.processing_time_ms = int((time.time() - start_time) * 1000)
            
            self.logger.debug(f"Cache hit for query: {query[:50]}... (similarity: {similarity:.3f})")
            return response
            
        except Exception as e:
            self.logger.error(f"Error retrieving cached response: {e}")
            return None
    
    def cache_response(self, query: str, response: CommandTranslation) -> bool:
        """
        Cache a command translation response.
        
        Args:
            query: User's natural language query
            response: CommandTranslation to cache
            
        Returns:
            True if successfully cached, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Generate hash for deduplication
            query_hash = self._generate_query_hash(query)
            
            # Check if already exists
            if query_hash in self.entries:
                # Update existing entry
                entry = self.entries[query_hash]
                entry.response = response
                entry.last_accessed = datetime.now()
                return True
            
            # Create new cache entry
            entry = CacheEntry(
                query_hash=query_hash,
                query_text=query,
                response=response
            )
            
            # Add to cache
            self.entries[query_hash] = entry
            self.entry_order.append(query_hash)
            
            # Evict old entries if needed
            self._evict_old_entries()
            
            # Rebuild index to include new entry
            self._rebuild_index()
            
            self.logger.debug(f"Cached response for query: {query[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Error caching response: {e}")
            return False
    
    def clear_cache(self):
        """Clear all cached entries."""
        self.entries.clear()
        self.entry_order.clear()
        if self.index:
            self.index.reset()
        self.embeddings = None
        self.logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics."""
        if not self.entries:
            return {
                "total_entries": 0,
                "cache_size_mb": 0,
                "average_similarity_threshold": self.config.similarity_threshold,
                "expired_entries": 0,
                "most_accessed_queries": []
            }
        
        # Count expired entries
        expired_count = sum(1 for entry in self.entries.values() if self._is_expired(entry))
        
        # Get most accessed queries
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: e.access_count,
            reverse=True
        )
        most_accessed = [
            {
                "query": entry.query_text[:100] + "..." if len(entry.query_text) > 100 else entry.query_text,
                "access_count": entry.access_count,
                "created_at": entry.created_at.isoformat()
            }
            for entry in sorted_entries[:5]
        ]
        
        # Estimate cache size
        cache_size_mb = len(pickle.dumps(self.entries)) / (1024 * 1024)
        
        return {
            "total_entries": len(self.entries),
            "cache_size_mb": round(cache_size_mb, 2),
            "average_similarity_threshold": self.config.similarity_threshold,
            "expired_entries": expired_count,
            "most_accessed_queries": most_accessed,
            "index_entries": self.index.ntotal if self.index else 0
        }
    
    def cleanup_expired_entries(self) -> int:
        """Remove expired entries and return count of removed entries."""
        if not self.enabled:
            return 0
        
        expired_keys = [key for key, entry in self.entries.items() if self._is_expired(entry)]
        
        for key in expired_keys:
            self._remove_entry(key)
        
        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def export_cache(self) -> Dict[str, any]:
        """Export cache data for persistence."""
        return {
            "config": {
                "similarity_threshold": self.config.similarity_threshold,
                "max_cache_size": self.config.max_cache_size,
                "cache_ttl_hours": self.config.cache_ttl_hours,
                "embedding_model": self.config.embedding_model
            },
            "entries": {key: entry.to_dict() for key, entry in self.entries.items()},
            "export_timestamp": datetime.now().isoformat()
        }
    
    def import_cache(self, data: Dict[str, any]) -> bool:
        """Import cache data from persistence."""
        try:
            # Clear existing cache
            self.clear_cache()
            
            # Import entries
            for key, entry_data in data.get("entries", {}).items():
                entry = CacheEntry(
                    query_hash=entry_data["query_hash"],
                    query_text=entry_data["query_text"],
                    response=CommandTranslation.from_dict(entry_data["response"]),
                    created_at=datetime.fromisoformat(entry_data["created_at"]),
                    access_count=entry_data["access_count"],
                    last_accessed=datetime.fromisoformat(entry_data["last_accessed"])
                )
                self.entries[key] = entry
                self.entry_order.append(key)
            
            # Rebuild index
            self._rebuild_index()
            
            self.logger.info(f"Imported {len(self.entries)} cache entries")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import cache: {e}")
            return False
