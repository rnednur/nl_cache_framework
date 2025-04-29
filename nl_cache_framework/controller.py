import logging
from typing import List, Dict, Optional, Any
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, JSON, Float, Boolean, DateTime, Text
from sqlalchemy.exc import SQLAlchemyError
import json
import datetime
from scipy.spatial.distance import cosine

# Local imports within the library
from .models import Text2SQLCache, TemplateType
from .similarity import Text2SQLSimilarity

logger = logging.getLogger(__name__)


class Text2SQLController:
    """Controller for managing Text2SQL cache operations."""

    def __init__(
        self,
        db_session: Session,
        similarity_model_name: str = "sentence-transformers/all-mpnet-base-v2",
    ):
        """
        Initialize the Text2SQL controller.

        Args:
            db_session: An active SQLAlchemy Session object for database interactions.
            similarity_model_name: Name of the sentence transformer model to use for embeddings.

        Raises:
            ValueError: If db_session is None.
        """
        if db_session is None:
            raise ValueError(
                "db_session cannot be None. Please provide an active SQLAlchemy session."
            )

        self.session = db_session
        self.similarity_util = Text2SQLSimilarity(model_name=similarity_model_name)
        logger.info(
            f"Text2SQLController initialized with model: {similarity_model_name}"
        )

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Get vector embedding for a text string using the similarity utility.

        Args:
            text: Text to embed.

        Returns:
            Numpy array containing the embedding or None if embedding fails.

        Raises:
            Exception: If embedding generation fails unexpectedly (logged).
        """
        try:
            embedding = self.similarity_util.get_embedding(text)
            if embedding is None:
                logger.warning(f"Could not generate embedding for text: {text[:50]}...")
                return None
            # Ensure it's a 1D array if a single string was passed
            return embedding[0] if embedding.ndim > 1 else embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def _compute_string_similarity(self, s1: str, s2: str) -> float:
        """
        Compute string similarity using the similarity utility.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score between 0.0 and 1.0

        Raises:
            Exception: If similarity computation fails unexpectedly (logged).
        """
        try:
            return self.similarity_util.compute_string_similarity(s1, s2)
        except Exception as e:
            logger.error(f"Error computing string similarity: {e}")
            return 0.0

    def add_query(
        self,
        nl_query: str,
        template: str,
        template_type: str = TemplateType.SQL,
        entity_replacements: Optional[Dict[str, Any]] = None,
        reasoning_trace: Optional[str] = None,
        tags: Optional[List[str]] = None,
        suggested_visualization: Optional[str] = None,
        database_name: Optional[str] = None,
        schema_name: Optional[str] = None,
        catalog_id: Optional[int] = None,
        is_template: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Add a new query to the cache.

        Args:
            nl_query: The natural language query.
            template: The template (SQL, URL, API spec, etc.).
            template_type: Type of the template (sql, url, api, workflow).
            entity_replacements: Optional dictionary of entity replacements.
            reasoning_trace: Optional explanation of the template.
            tags: Optional list of tags for categorization.
            suggested_visualization: Optional hint for visualization.
            database_name: Optional target database identifier.
            schema_name: Optional target schema identifier.
            catalog_id: Optional catalog identifier.
            is_template: Flag indicating if this entry contains placeholders.

        Returns:
            Dictionary representation of the created cache entry.

        Raises:
            SQLAlchemyError: If a database error occurs.
            ValueError: If required fields are missing or invalid.
        """
        if not nl_query or not template:
            raise ValueError("nl_query and template are required")

        try:
            # Create and get embedding
            embedding_array = self._get_embedding(nl_query)

            # If is_template is not specified, determine it from entity_replacements
            if is_template is None:
                is_template = bool(entity_replacements)

            # Create cache entry
            cache_entry = Text2SQLCache(
                is_template=is_template,
                template_type=template_type,
                nl_query=nl_query,
                template=template,
                entity_replacements=entity_replacements,
                reasoning_trace=reasoning_trace,
                tags=tags,
                suggested_visualization=suggested_visualization,
                database_name=database_name,
                schema_name=schema_name,
                catalog_id=catalog_id,
            )
            # Use the property setter to handle numpy array -> list conversion
            cache_entry.embedding = embedding_array

            # Store in database using the provided session
            self.session.add(cache_entry)
            self.session.flush()  # Assign ID before commit/return
            self.session.commit()

            # Convert to dictionary before returning
            result = cache_entry.to_dict()
            logger.info(f"Added new cache entry with ID {result.get('id')}")
            return result

        except SQLAlchemyError as e:
            logger.error(
                f"Database error adding query to cache: {str(e)}", exc_info=True
            )
            self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"Failed to add query to cache: {str(e)}", exc_info=True)
            self.session.rollback()
            raise ValueError(f"Error creating cache entry: {str(e)}")

    def search_query(
        self,
        nl_query: str,
        template_type: Optional[str] = None,
        search_method: str = "auto",
        similarity_threshold: float = 0.8,
        database_name: Optional[str] = None,
        schema_name: Optional[str] = None,
        catalog_id: Optional[int] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for a natural language query in the cache.

        Args:
            nl_query: Natural language query to search for.
            template_type: Optional filter for template type.
            search_method: Search method ('exact', 'string', 'vector', or 'auto').
            similarity_threshold: Minimum similarity threshold (0.0 to 1.0).
            database_name: Optional filter by database name.
            schema_name: Optional filter by schema name.
            catalog_id: Optional filter by catalog ID.
            limit: Maximum number of results to return.

        Returns:
            List of matching cache entries as dictionaries, including 'similarity'
            and 'match_type'. Sorted by relevance. Returns empty list on error.

        Raises:
            ValueError: If search_method is invalid.
            SQLAlchemyError: If a database error occurs during candidate fetching (logged, returns []).
            Exception: If similarity computation fails unexpectedly (logged, returns []).
        """
        if not nl_query or not nl_query.strip():
            logger.warning("Empty query provided to search_query")
            return []

        valid_search_methods = ["exact", "string", "vector", "auto"]
        if search_method not in valid_search_methods:
            raise ValueError(
                f"Invalid search_method. Must be one of: {', '.join(valid_search_methods)}"
            )

        results = []
        similarity_threshold = max(0.0, min(1.0, similarity_threshold))

        try:
            # --- Get Query Embedding ---
            query_embedding = self._get_embedding(nl_query)
            if query_embedding is None:
                logger.warning(f"Could not generate embedding for search query: {nl_query[:50]}..." " Skipping similarity search.")
                # Optionally, could still perform exact match here if needed
                return []

            # --- Build Base Query & Fetch Candidates ---
            # Fetch all potentially relevant candidates first
            base_query = self.session.query(Text2SQLCache).filter(
                Text2SQLCache.is_valid == True
            )
            # Add existing filters
            if template_type:
                base_query = base_query.filter(Text2SQLCache.template_type == template_type)
            if database_name:
                base_query = base_query.filter(Text2SQLCache.database_name == database_name)
            if schema_name:
                base_query = base_query.filter(Text2SQLCache.schema_name == schema_name)
            if catalog_id is not None:
                base_query = base_query.filter(Text2SQLCache.catalog_id == catalog_id)

            # Fetch all candidates matching filters
            # WARNING: This can be inefficient for large tables!
            candidate_entries = base_query.all()
            if not candidate_entries:
                logger.debug("No candidate entries found matching filters.")
                return []

            logger.debug(f"Fetched {len(candidate_entries)} candidates for similarity check.")

            # --- Calculate Similarities in Python ---
            # Filter entries that have embeddings and calculate similarity
            entries_with_embeddings = []
            embeddings_to_compare = []
            for entry in candidate_entries:
                entry_embedding = entry.embedding # Use property getter
                if entry_embedding is not None:
                    entries_with_embeddings.append(entry)
                    embeddings_to_compare.append(entry_embedding)

            if not entries_with_embeddings:
                logger.debug("No candidates with valid embeddings found.")
                return []

            # Use the similarity utility to compute scores
            similarities = self.similarity_util.compute_vector_similarities(
                query_embedding, embeddings_to_compare
            )

            # Combine entries with scores and filter by threshold
            scored_results = []
            for i, entry in enumerate(entries_with_embeddings):
                similarity_score = float(similarities[i])
                if similarity_score >= similarity_threshold:
                    entry_dict = entry.to_dict()
                    entry_dict['similarity'] = similarity_score
                    entry_dict['match_type'] = 'vector' # Still call it vector for consistency
                    scored_results.append(entry_dict)

            # Sort by similarity and limit
            results = sorted(scored_results, key=lambda x: x["similarity"], reverse=True)[:limit]

            logger.info(f"In-memory similarity search found {len(results)} results for query: {nl_query[:50]}...")
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error during search: {str(e)}", exc_info=True)
            self.session.rollback()
            return [] # Return empty list on DB error
        except Exception as e:
            # Catch potential errors during embedding or similarity calculation
            logger.error(f"Unexpected error during search: {str(e)}", exc_info=True)
            self.session.rollback() # Rollback on any exception during search logic
            return []

    def get_query_by_id(self, query_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a query by ID and increment its usage count.

        Args:
            query_id: ID of the query to retrieve.

        Returns:
            Query as a dictionary or None if not found.

        Raises:
            SQLAlchemyError: If a database error occurs (session rolled back).
        """
        try:
            query = (
                self.session.query(Text2SQLCache)
                .filter(Text2SQLCache.id == query_id)
                .first()
            )

            if query:
                result = query.to_dict()
                # Increment usage count
                query.usage_count = (query.usage_count or 0) + 1
                self.session.commit()
                return result
            else:
                return None

        except Exception as e:
            logger.error(
                f"Failed to get query by ID {query_id}: {str(e)}", exc_info=True
            )
            self.session.rollback()
            raise

    def update_query(
        self, query_id: int, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a query entry.

        Args:
            query_id: ID of the query to update.
            updates: Dictionary of fields to update. Keys should match Text2SQLCache attributes.
                     Special handling for 'nl_query' (recomputes embedding).

        Returns:
            Updated query as a dictionary or None if not found.

        Raises:
            SQLAlchemyError: If a database error occurs (session rolled back).
            Exception: If embedding generation fails for updated nl_query (logged).
        """
        try:
            query = (
                self.session.query(Text2SQLCache)
                .filter(Text2SQLCache.id == query_id)
                .first()
            )

            if not query:
                return None

            update_data = updates.copy()

            # Handle special case for nl_query to update embedding
            if "nl_query" in update_data and update_data["nl_query"] != query.nl_query:
                new_embedding_array = self._get_embedding(update_data["nl_query"])
                # Use the property setter to handle numpy array -> list conversion
                query.embedding = new_embedding_array
                if new_embedding_array is None:
                     logger.warning(
                        "Failed to generate new embedding during update, vector embedding set to null."
                     )
            # Remove embedding fields from direct updates as they are handled above
            update_data.pop('embedding', None)
            update_data.pop('vector_embedding', None)

            # If entity_replacements is explicitly updated, adjust is_template
            if "entity_replacements" in update_data:
                entity_replacements = update_data["entity_replacements"]
                query.is_template = bool(entity_replacements)

            # Update other fields
            for key, value in update_data.items():
                # Skip fields handled specially above
                if key in ['nl_query']: # nl_query already applied if present
                    continue
                if hasattr(query, key):
                    setattr(query, key, value)
                else:
                    logger.warning(
                        f"Attempted to update non-existent attribute '{key}' on Text2SQLCache"
                    )

            # Ensure updated_at is set (handle type change from model)
            query.updated_at = datetime.datetime.utcnow()

            self.session.commit()
            result = query.to_dict()
            logger.info(f"Updated cache entry with ID {query_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to update query {query_id}: {str(e)}", exc_info=True)
            self.session.rollback()
            raise

    def invalidate_query(self, query_id: int, reason: Optional[str] = None) -> bool:
        """
        Invalidate a cache entry.

        Args:
            query_id: ID of the query to invalidate.
            reason: Optional reason for invalidation.

        Returns:
            True if successful, False if query not found.

        Raises:
            SQLAlchemyError: If a database error occurs (session rolled back).
        """
        try:
            query = (
                self.session.query(Text2SQLCache)
                .filter(Text2SQLCache.id == query_id)
                .first()
            )

            if not query:
                return False

            query.is_valid = False
            query.invalidation_reason = reason
            query.updated_at = int(datetime.datetime.utcnow().timestamp())

            self.session.commit()
            logger.info(f"Invalidated cache entry with ID {query_id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to invalidate query {query_id}: {str(e)}", exc_info=True
            )
            self.session.rollback()
            raise

    def delete_query(self, query_id: int) -> bool:
        """
        Delete a cache entry.

        Args:
            query_id: ID of the query to delete.

        Returns:
            True if successful, False if query not found.

        Raises:
            SQLAlchemyError: If a database error occurs (session rolled back).
        """
        try:
            query = (
                self.session.query(Text2SQLCache)
                .filter(Text2SQLCache.id == query_id)
                .first()
            )

            if not query:
                return False

            self.session.delete(query)
            self.session.commit()
            logger.info(f"Deleted cache entry with ID {query_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete query {query_id}: {str(e)}", exc_info=True)
            self.session.rollback()
            raise

    def get_query_by_template_type(
        self, template_type: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get valid queries filtered by template type.

        Args:
            template_type: Type of template (e.g., 'sql', 'url').
            limit: Maximum number of results.

        Returns:
            List of matching queries as dictionaries, ordered by usage count descending.

        Raises:
            SQLAlchemyError: If a database error occurs.
        """
        try:
            queries = (
                self.session.query(Text2SQLCache)
                .filter(
                    Text2SQLCache.template_type == template_type,
                    Text2SQLCache.is_valid
                )
                .order_by(Text2SQLCache.usage_count.desc())
                .limit(limit)
                .all()
            )

            return [query.to_dict() for query in queries]

        except Exception as e:
            logger.error(
                f"Failed to get queries by template type '{template_type}': {str(e)}",
                exc_info=True,
            )
            raise

    def get_query_by_tags(
        self,
        tags: List[str],
        template_type: Optional[str] = None,
        match_all: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get valid queries by tags, optionally filtering by template type.

        Args:
            tags: List of tags to search for.
            template_type: Optional template type filter.
            match_all: If True, all tags must match; if False, any tag may match.

        Returns:
            List of matching queries as dictionaries.

        Raises:
            SQLAlchemyError: If a database error occurs during initial candidate fetch.
        """
        # Check if tags list is empty
        if not tags:
            return []

        try:
            # Base query for valid entries and optional template type
            base_query = self.session.query(Text2SQLCache).filter(
                Text2SQLCache.is_valid
            )
            if template_type:
                base_query = base_query.filter(
                    Text2SQLCache.template_type == template_type
                )

            # Fetch all potential candidates first
            # Optimization: If DB supports JSONB/Array containment (like PostgreSQL), use that.
            # For SQLite/simple JSON, we filter in Python.
            candidate_entries = base_query.all()

            results = []
            search_tags_set = set(tags)

            for entry in candidate_entries:
                entry_tags = entry.tags or []  # entry.tags should be a list
                if isinstance(entry_tags, list):
                    entry_tags_set = set(entry_tags)
                    # Check tag condition
                    if match_all:
                        if search_tags_set.issubset(entry_tags_set):
                            results.append(entry.to_dict())
                    else:
                        if not search_tags_set.isdisjoint(entry_tags_set):
                            results.append(entry.to_dict())
                else:
                    logger.warning(
                        f"Tags field for entry ID {entry.id} is not a list: {type(entry.tags)}. Skipping tag match."
                    )

            return results

        except Exception as e:
            logger.error(f"Failed to get queries by tags: {str(e)}", exc_info=True)
            raise

    # apply_entity_substitution might be better placed in the entity_substitution module
    # or called from there, passing the controller or session if needed for DB updates.
    # Keeping it here based on original structure for now.
    def apply_entity_substitution(
        self, template_id: int, new_entity_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Retrieve a template, apply provided entity values, and return results.
        Increments the usage count of the template.

        Args:
            template_id: ID of the template cache entry to use.
            new_entity_values: Dictionary mapping entity keys (from the template's
                               entity_replacements) to the new values to substitute.

        Returns:
            Dictionary containing original template, substituted template, type,
            replacement metadata, and applied values.

        Raises:
            ValueError: If template not found, invalid, or missing replacement info.
            SQLAlchemyError: If a database error occurs (session rolled back).
            Exception: If entity substitution processing fails.
        """
        from .entity_substitution import (
            Text2SQLEntitySubstitution,
        )  # Local import to avoid circularity if moved

        try:
            cache_entry = (
                self.session.query(Text2SQLCache)
                .filter(Text2SQLCache.id == template_id, Text2SQLCache.is_valid)
                .first()
            )

            if not cache_entry:
                raise ValueError(
                    f"Template with ID {template_id} not found or is invalid"
                )

            if not cache_entry.entity_replacements:
                # Maybe this is okay? Return original template? For now, raise error.
                raise ValueError(
                    f"Template with ID {template_id} does not have entity replacement information"
                )

            # Get the template and entity replacements
            original_template = cache_entry.template
            entity_replacements = cache_entry.entity_replacements

            # Apply substitution using the utility function
            substituted_template, mapping = (
                Text2SQLEntitySubstitution.extract_and_replace_entities(
                    nl_query="",  # Not needed when new_entity_values are provided
                    template=original_template,
                    entity_replacements=entity_replacements,
                    new_entity_values=new_entity_values,
                )
            )

            # Increment usage count
            cache_entry.usage_count = (cache_entry.usage_count or 0) + 1
            self.session.commit()

            result = {
                "original_template": original_template,
                "substituted_template": substituted_template,
                "template_type": cache_entry.template_type,
                "entity_replacements": entity_replacements,
                "applied_values": new_entity_values,
                "substitution_mapping": mapping,  # Include details of what was replaced
            }

            return result

        except Exception as e:
            logger.error(
                f"Failed to apply entity substitution for template ID {template_id}: {str(e)}",
                exc_info=True,
            )
            self.session.rollback()
            raise

    def delete_all_cache_entries(self) -> bool:
        """Deletes all entries from the cache table."""
        try:
            self.session.query(Text2SQLCache).delete()
            self.session.commit()
            logger.info("Deleted all cache entries")
            return True
        except Exception as e:
            logger.error(f"Failed to delete all cache entries: {str(e)}", exc_info=True)
            self.session.rollback()
            raise

    def batch_insert(self, entries: List[Dict[str, Any]]) -> List[Text2SQLCache]:
        """Batch insert multiple cache entries."""
        if not entries:
            return []
        new_entries = [Text2SQLCache(**entry) for entry in entries]
        self.session.add_all(new_entries)
        self.session.commit()
        return new_entries

    def _get_similar_queries_vector_search(
        self,
        nl_query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        embedding = self._get_embedding(nl_query)
        query_vector = np.array(embedding).astype(np.float32)

        # Perform KNN search
        # Ensure the index is trained if necessary
        if not self.vector_index.is_trained:
            # This check might be redundant if index is added incrementally
            # Or handle training explicitly if needed before search
            logger.warning("Vector index is not trained. Search might fail or be slow.")

        # Perform search
        distances, indices = self.vector_index.search(query_vector.reshape(1, -1), k=limit * 2) # Search more initially

        # Filter results by threshold and map indices back to IDs
        filtered_results = []
        for distance, index in zip(distances[0], indices[0]):
            if distance <= self.similarity_threshold:
                query = self.session.query(Text2SQLCache).get(index)
                if query:
                    filtered_results.append(query.to_dict())

        return filtered_results
