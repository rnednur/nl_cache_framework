"""
Utility classes and functions for computing text similarity.

Provides:
- String similarity using SequenceMatcher.
- Vector similarity using Sentence Transformers.
- Batch processing capabilities.
"""

from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer, util
from difflib import SequenceMatcher
import re
import logging

logger = logging.getLogger(__name__)


class Text2SQLSimilarity:
    """Handles text similarity calculations using different methods."""

    # Cache loaded models to avoid reloading
    _model_cache: Dict[str, SentenceTransformer] = {}

    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        """Initialize the similarity utility.

        Args:
            model_name: The name of the Sentence Transformer model to load.
                        Defaults to 'sentence-transformers/all-mpnet-base-v2'.
        """
        self.model_name = model_name
        self.model = self._load_model(model_name)
        if self.model is None:
            logger.warning(
                f"Failed to load model {model_name}. Some functionality will be limited."
            )

    @classmethod
    def _load_model(cls, model_name: str) -> Optional[SentenceTransformer]:
        """
        Load or retrieve a cached SentenceTransformer model.

        Args:
            model_name: Name or path of the model to load.

        Returns:
            SentenceTransformer model or None if loading fails.
        """
        if model_name in cls._model_cache:
            logger.debug(f"Using cached SentenceTransformer model: {model_name}")
            return cls._model_cache[model_name]

        try:
            logger.info(f"Loading SentenceTransformer model: {model_name}")
            model = SentenceTransformer(model_name)
            cls._model_cache[model_name] = model
            logger.info(f"Successfully loaded model: {model_name}")
            return model
        except Exception as e:
            logger.error(
                f"Failed to load sentence transformer model '{model_name}': {str(e)}",
                exc_info=True,
            )
            return None

    def get_embedding(self, text: List[str]) -> Optional[np.ndarray]:
        """Generate sentence embeddings for a list of text strings.

        Args:
            text: A list of strings to embed.

        Returns:
            A NumPy array containing the embeddings (one row per string),
            or None if the model is not loaded or embedding fails.
        """
        if not self.model:
            logger.error("Sentence transformer model not loaded. Cannot get embeddings.")
            return None
        if not text:
            return np.array([])

        try:
            # Ensure all elements are strings
            processed_text = [str(t) if t is not None else "" for t in text]
            embeddings = self.model.encode(processed_text, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}", exc_info=True)
            return None

    def compute_string_similarity(self, s1: str, s2: str) -> float:
        """Compute similarity between two strings using SequenceMatcher with word coverage.

        Args:
            s1: First string.
            s2: Second string.

        Returns:
            Similarity score between 0.0 and 1.0, combining word coverage and sequence similarity.
        """
        # Ensure inputs are strings
        s1 = str(s1) if s1 is not None else ""
        s2 = str(s2) if s2 is not None else ""
        
        # Get word sets
        words1 = set(s1.lower().split())
        words2 = set(s2.lower().split())
        
        # Minimum word length requirement (reduced to 2 to include more words)
        MIN_WORD_LENGTH = 2
        words1 = {w for w in words1 if len(w) >= MIN_WORD_LENGTH}
        words2 = {w for w in words2 if len(w) >= MIN_WORD_LENGTH}
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate word coverage using a more lenient approach
        common_words = words1.intersection(words2)
        # Use min instead of max to be more lenient with partial matches
        word_coverage = len(common_words) / min(len(words1), len(words2))
        
        # Calculate sequence similarity
        sequence_score = SequenceMatcher(None, s1, s2).ratio()
        
        # Minimum thresholds (reduced to be more lenient)
        MIN_WORD_COVERAGE = 0.2  # At least 20% of words must match
        MIN_SEQUENCE_SIMILARITY = 0.3  # At least 30% sequence similarity
        
        if word_coverage < MIN_WORD_COVERAGE or sequence_score < MIN_SEQUENCE_SIMILARITY:
            return 0.0
        
        # Weight the scores (60% word coverage, 40% sequence similarity)
        # This gives more weight to sequence similarity to catch similar words
        return 0.6 * word_coverage + 0.4 * sequence_score

    def compute_cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two vector embeddings.

        Args:
            emb1: First embedding (1D NumPy array).
            emb2: Second embedding (1D NumPy array).

        Returns:
            Cosine similarity score between -1.0 and 1.0.
        """
        try:
            # Ensure embeddings are NumPy arrays
            if not isinstance(emb1, np.ndarray):
                emb1 = np.array(emb1)
            if not isinstance(emb2, np.ndarray):
                emb2 = np.array(emb2)

            # Handle potential shape mismatches or zero vectors if necessary
            if emb1.shape != emb2.shape:
                logger.warning(f"Embedding shape mismatch: {emb1.shape} vs {emb2.shape}")
                return 0.0
            if np.all(emb1 == 0) or np.all(emb2 == 0):
                return 0.0

            # Compute cosine similarity
            similarity = util.cos_sim(emb1, emb2)
            # util.cos_sim returns a tensor; extract the scalar value
            score = float(similarity.item())
            
            # Apply stricter scoring
            # 1. Normalize to 0-1 range (cosine similarity is -1 to 1)
            score = (score + 1) / 2
            
            # 2. Apply non-linear scaling to make the scoring more strict
            # This will make scores below 0.7 much lower
            if score < 0.7:
                score = score * 0.5  # Halve the score for low similarities
            
            return score
        except Exception as e:
            logger.error(f"Error computing cosine similarity: {e}")
            return 0.0

    def compute_vector_similarities(self, query_emb: np.ndarray, candidate_embs: List[np.ndarray]) -> List[float]:
        """Compute cosine similarities between a query embedding and a list of candidate embeddings.

        Args:
            query_emb: The query embedding (1D NumPy array).
            candidate_embs: A list of candidate embeddings (1D NumPy arrays).

        Returns:
            A list of cosine similarity scores, one for each candidate.
        """
        if not self.model:
            logger.error("Model not loaded. Cannot compute vector similarities.")
            return [0.0] * len(candidate_embs)
        if query_emb is None or not candidate_embs:
            return [0.0] * len(candidate_embs)

        try:
            # Ensure candidates are stacked correctly for util.cos_sim
            candidate_embs_array = np.array(candidate_embs)
            similarities = util.cos_sim(query_emb, candidate_embs_array)
            # Return similarities as a list of floats
            return similarities.flatten().tolist()
        except Exception as e:
            logger.error(f"Error computing batch vector similarities: {e}", exc_info=True)
            return [0.0] * len(candidate_embs)

    def batch_compute_similarity(
        self, query: str, candidates: List[str], method: str = "string"
    ) -> List[float]:
        """Compute similarity between a query and a list of candidates using the specified method.

        Args:
            query: The query string.
            candidates: A list of candidate strings.
            method: The similarity method ('string' or 'vector').

        Returns:
            A list of similarity scores.

        Raises:
            ValueError: If an invalid method is specified.
        """
        if method == "string":
            return [
                self.compute_string_similarity(query, cand) for cand in candidates
            ]
        elif method == "vector":
            query_embedding = self.get_embedding([query])
            if query_embedding is None:
                logger.error("Failed to generate embedding for the query.")
                return [0.0] * len(candidates)

            candidate_embeddings = self.get_embedding(candidates)
            if candidate_embeddings is None:
                 logger.error("Failed to generate embeddings for candidates.")
                 return [0.0] * len(candidates)

            return self.compute_vector_similarities(query_embedding[0], candidate_embeddings)
        else:
            raise ValueError(f"Invalid similarity method: {method}")

    def find_most_similar(
        self,
        query: str,
        candidates: List[str],
        candidate_embeddings: Optional[List[Optional[np.ndarray]]] = None,
        method: str = "vector",
        threshold: float = 0.7,
    ) -> List[Tuple[int, float]]:
        """
        Find the most similar candidates to a query.

        Args:
            query: Query string.
            candidates: List of candidate strings (required for string similarity,
                      optional for vector if embeddings are provided).
            candidate_embeddings: Pre-computed embeddings for candidates (optional, for vector).
            method: Similarity method ('vector' or 'string').
            threshold: Minimum similarity threshold.

        Returns:
            List of (candidate_index, similarity_score) tuples for candidates above threshold,
            sorted by similarity descending.
        """
        similarities: Optional[List[float]] = None

        if method == "vector":
            if not self.model:
                logger.error(
                    "Vector similarity requested but embedding model is not available."
                )
                return []
            query_embedding = self.get_embedding([query])
            if query_embedding is None:
                logger.error("Failed to generate embedding for the query.")
                return []
            # Ensure query_embedding is 1D
            if query_embedding.ndim > 1:
                query_embedding = query_embedding[0]

            if candidate_embeddings:
                if len(candidate_embeddings) != len(candidates):
                    logger.warning(
                        "Mismatch between number of candidates and provided embeddings."
                    )
                    # Decide handling: error, ignore embeddings, etc. For now, calculate missing ones.
                    # This part might need adjustment based on expected usage.
                    candidate_embeddings = self.get_embedding(candidates)
                    if candidate_embeddings is None:
                        return []
                similarities = [
                    (
                        self.compute_cosine_similarity(query_embedding, cand_emb)
                        if cand_emb is not None
                        else 0.0
                    )  # Handle potential None embeddings
                    for cand_emb in candidate_embeddings
                ]
            else:
                # Calculate embeddings if not provided
                cand_embeds_calc = self.get_embedding(candidates)
                if cand_embeds_calc is None:
                    return []
                similarities = [
                    self.compute_cosine_similarity(query_embedding, cand_emb)
                    for cand_emb in cand_embeds_calc
                ]

        elif method == "string":
            similarities = [
                self.compute_string_similarity(query, candidate)
                for candidate in candidates
            ]
        else:
            logger.error(f"Unknown similarity method requested: {method}")
            raise ValueError(f"Unknown similarity method: {method}")

        if similarities is None:
            return []  # Should only happen if vector embedding failed

        # Log top 5 similarity scores for debugging
        top_scores = sorted(enumerate(similarities), key=lambda x: x[1], reverse=True)[:5]
        logger.info(f"Query: {query}")
        logger.info("Top 5 similarity scores:")
        for idx, score in top_scores:
            logger.info(f"Score: {score:.4f} - Candidate: {candidates[idx]}")

        # Filter and sort by similarity
        similar_indices = [
            (i, score) for i, score in enumerate(similarities) if score >= threshold
        ]
        similar_indices.sort(key=lambda x: x[1], reverse=True)

        return similar_indices

    # Entity extraction is less about similarity and more about NLP/parsing.
    # It might be better placed in its own utility or within entity_substitution.
    # Keeping a basic version here for now based on original code.
    @staticmethod
    def extract_entities(query: str) -> Dict[str, Any]:
        """
        Extract potential entities from a query.
        This is a placeholder implementation - use a proper NER library in production.

        Args:
            query: Query string.

        Returns:
            Dictionary of entity types and values.
        """
        entities = {}
        # Extract dates (simple regex pattern - adjust as needed)
        # Example: Matches YYYY-MM-DD, MM/DD/YYYY, M/D/YY
        date_pattern = (
            r"\b(\d{4}-\d{1,2}-\d{1,2})\b|\b(\d{1,2}/\d{1,2}/(\d{2}|\d{4}))\b"
        )
        dates = [match[0] or match[1] for match in re.findall(date_pattern, query)]
        if dates:
            entities["dates"] = list(set(dates))  # Use set to remove duplicates

        # Extract numbers (integers and decimals)
        number_pattern = r"\b\d+(\.\d+)?\b"
        numbers = re.findall(number_pattern, query)
        # Flatten the list of tuples from findall and remove empty strings
        numbers = [num[0] for num in numbers if num[0]]
        if numbers:
            entities["numbers"] = list(set(numbers))

        # Extract potential named entities (simple: Capitalized words not at sentence start)
        # This is VERY basic and error-prone. Use spaCy, NLTK, etc. for real NER.
        # Matches sequences of capitalized words.
        named_entity_pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
        # Avoid matching words at the very beginning of the string for simplicity
        named_entities = [
            match
            for match in re.findall(named_entity_pattern, query)
            if not query.startswith(match)
        ]
        if named_entities:
            entities["named_entities"] = list(set(named_entities))

        return entities
