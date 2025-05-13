import logging
from typing import List, Dict, Optional, Any
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, JSON, Float, Boolean, DateTime, Text
from sqlalchemy.exc import SQLAlchemyError
import json
import datetime
from scipy.spatial.distance import cosine
import os

# Local imports within the library
from .models import Text2SQLCache, TemplateType, Status, CacheAuditLog, UsageLog
from .similarity import Text2SQLSimilarity
from .entity_substitution import Text2SQLEntitySubstitution

# Import LLM service for enhanced completions
try:
    from llm_service import LLMService
except ImportError:
    LLMService = None

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
            embedding = self.similarity_util.get_embedding([text])
            if embedding is None or len(embedding) == 0:
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
        catalog_type: Optional[str] = None,
        catalog_subtype: Optional[str] = None,
        catalog_name: Optional[str] = None,
        is_template: Optional[bool] = None,
        status: str = Status.ACTIVE,
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
            catalog_type: Optional catalog type to filter by.
            catalog_subtype: Optional catalog subtype to filter by.
            catalog_name: Optional catalog name to filter by.
            is_template: Flag indicating if this entry contains placeholders.
            status: Status of the cache entry (pending, active, archive). Defaults to ACTIVE.

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
                catalog_type=catalog_type,
                catalog_subtype=catalog_subtype,
                catalog_name=catalog_name,
                status=status,
            )
            # Use the property setter to handle numpy array -> list conversion
            cache_entry.embedding = embedding_array

            # Store in database using the provided session
            self.session.add(cache_entry)
            self.session.flush()  # Assign ID before commit/return
            self.session.commit()

            # Log the creation in audit log
            audit_log = CacheAuditLog(
                cache_entry_id=cache_entry.id,
                changed_field="creation",
                old_value=None,
                new_value=None,
                change_reason="New cache entry created"
            )
            self.session.add(audit_log)
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
        search_method: str = "vector",
        similarity_threshold: float = 0.8,
        limit: int = 5,
        catalog_type: Optional[str] = None,
        catalog_subtype: Optional[str] = None,
        catalog_name: Optional[str] = None,
        status: Optional[str] = Status.ACTIVE,
    ) -> List[Dict[str, Any]]:
        """Search for similar queries in the cache.

        Args:
            nl_query: The natural language query to search for.
            template_type: Optional template type to filter by.
            search_method: Method to use for similarity search ('exact', 'string', 'vector', or 'auto').
            similarity_threshold: Minimum similarity score (0.0 to 1.0).
            limit: Maximum number of results to return.
            catalog_type: Optional catalog type to filter by.
            catalog_subtype: Optional catalog subtype to filter by.
            catalog_name: Optional catalog name to filter by.
            status: Optional status to filter by (pending, active, archive). Defaults to ACTIVE.

        Returns:
            List of matching cache entries with similarity scores.
        """
        if not nl_query:
            return []

        # Build the base query with filters applied at the database level
        query = self.session.query(Text2SQLCache)
        if status:
            query = query.filter(Text2SQLCache.status == status)
        if template_type:
            query = query.filter(Text2SQLCache.template_type == template_type)
        if catalog_type:
            query = query.filter(Text2SQLCache.catalog_type == catalog_type)
        if catalog_subtype:
            query = query.filter(Text2SQLCache.catalog_subtype == catalog_subtype)
        if catalog_name:
            query = query.filter(Text2SQLCache.catalog_name == catalog_name)

        # Fetch the filtered candidates
        candidates = [c.to_dict() for c in query.all()]
        if not candidates:
            return []
        
        # Get embeddings for vector similarity if needed
        candidate_embeddings_list = []
        embedding_field_name = 'embedding'  # Default field name
        # Check if the field might be named differently
        if candidates and 'vector_embedding' in candidates[0]:
            embedding_field_name = 'vector_embedding'
        for c in candidates:
            emb = c.get(embedding_field_name)
            if emb is not None and len(emb) > 0:
                candidate_embeddings_list.append(np.array(emb))
            else:
                candidate_embeddings_list.append(None)
        logger.info(f"Using stored embeddings for {len(candidate_embeddings_list)} candidates")

        # Determine search method if auto
        if search_method == "auto":
            if len(candidates) > 100:
                search_method = "vector"
            else:
                search_method = "string"
        logger.info(f"Method: {search_method}, Threshold: {similarity_threshold}")

        # Perform search based on method
        if search_method == "exact":
            results = [
                c for c in candidates if c.get("nl_query", "").lower() == nl_query.lower()
            ]
            for r in results:
                r["similarity"] = 1.0 if r.get("nl_query", "").lower() == nl_query.lower() else 0.0
        elif search_method == "string":
            results = []
            for c in candidates:
                sim = self._compute_string_similarity(nl_query, c.get("nl_query", ""))
                if sim >= similarity_threshold:
                    c["similarity"] = sim
                    results.append(c)
        elif search_method == "vector":
            from thinkforge.models import USE_PG_VECTOR
            if USE_PG_VECTOR:
                try:
                    from pgvector.sqlalchemy import Vector
                    query_emb = self._get_embedding(nl_query)
                    if query_emb is None:
                        logger.warning("Failed to get embedding for query, falling back to string search")
                        results = []
                        for c in candidates:
                            sim = self._compute_string_similarity(nl_query, c.get("nl_query", ""))
                            if sim >= similarity_threshold:
                                c["similarity"] = sim
                                results.append(c)
                    else:
                        results = []
                        # Use pg_vector for similarity search
                        vector_query = self.session.query(Text2SQLCache).filter(
                            Text2SQLCache.status == status if status else Text2SQLCache.status == Status.ACTIVE
                        )
                        if catalog_type:
                            vector_query = vector_query.filter(Text2SQLCache.catalog_type == catalog_type)
                        if catalog_subtype:
                            vector_query = vector_query.filter(Text2SQLCache.catalog_subtype == catalog_subtype)
                        if catalog_name:
                            vector_query = vector_query.filter(Text2SQLCache.catalog_name == catalog_name)
                        if template_type:
                            vector_query = vector_query.filter(Text2SQLCache.template_type == template_type)
                        # Perform vector similarity search using pg_vector
                        vector_query = vector_query.order_by(Text2SQLCache.pg_vector.cosine_distance(query_emb)).limit(limit * 2)
                        pg_results = vector_query.all()
                        for res in pg_results:
                            res_dict = res.to_dict()
                            # Calculate similarity for display purposes
                            sim = self.similarity_util.compute_cosine_similarity(query_emb, res.embedding) if res.embedding is not None else 0.0
                            if sim >= similarity_threshold:
                                res_dict["similarity"] = float(sim)
                                results.append(res_dict)
                        logger.info(f"Found {len(results)} matches above threshold using pg_vector")
                except ImportError:
                    logger.warning("pg_vector not available, falling back to standard vector search")
                    query_emb = self._get_embedding(nl_query)
                    if query_emb is None:
                        logger.warning("Failed to get embedding for query, falling back to string search")
                        results = []
                        for c in candidates:
                            sim = self._compute_string_similarity(nl_query, c.get("nl_query", ""))
                            if sim >= similarity_threshold:
                                c["similarity"] = sim
                                results.append(c)
                    else:
                        results = []
                        valid_indices = [i for i, emb in enumerate(candidate_embeddings_list) if emb is not None]
                        valid_embs = [candidate_embeddings_list[i] for i in valid_indices]
                        if valid_embs:
                            similarities = self.similarity_util.compute_vector_similarities(query_emb, valid_embs)
                            for idx, sim in zip(valid_indices, similarities):
                                if sim >= similarity_threshold:
                                    candidates[idx]["similarity"] = float(sim)
                                    results.append(candidates[idx])
                        logger.info(f"Found {len(results)} matches above threshold")
            else:
                query_emb = self._get_embedding(nl_query)
                if query_emb is None:
                    logger.warning("Failed to get embedding for query, falling back to string search")
                    results = []
                    for c in candidates:
                        sim = self._compute_string_similarity(nl_query, c.get("nl_query", ""))
                        if sim >= similarity_threshold:
                            c["similarity"] = sim
                            results.append(c)
                else:
                    results = []
                    valid_indices = [i for i, emb in enumerate(candidate_embeddings_list) if emb is not None]
                    valid_embs = [candidate_embeddings_list[i] for i in valid_indices]
                    if valid_embs:
                        similarities = self.similarity_util.compute_vector_similarities(query_emb, valid_embs)
                        for idx, sim in zip(valid_indices, similarities):
                            if sim >= similarity_threshold:
                                candidates[idx]["similarity"] = float(sim)
                                results.append(candidates[idx])
                    logger.info(f"Found {len(results)} matches above threshold")
        else:
            raise ValueError(f"Unknown search method: {search_method}")

        # Sort by similarity if available, otherwise by ID
        results.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)
        return results[:limit]

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
        self, query_id: int, updates: Dict[str, Any], change_reason: Optional[str] = None, changed_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing query in the cache.

        Args:
            query_id: ID of the query to update.
            updates: Dictionary of fields to update.
            change_reason: Optional reason for the update.
            changed_by: Optional identifier of who made the change.

        Returns:
            Updated cache entry as a dictionary, or None if not found.

        Raises:
            SQLAlchemyError: If a database error occurs.
        """
        try:
            cache_entry = self.session.query(Text2SQLCache).filter(Text2SQLCache.id == query_id).first()
            if not cache_entry:
                logger.warning(f"Cache entry {query_id} not found for update")
                return None

            # Track changes for audit log
            changes = []

            # Handle embedding update if nl_query is updated
            if "nl_query" in updates:
                new_nl_query = updates["nl_query"]
                if new_nl_query and new_nl_query != cache_entry.nl_query:
                    embedding_array = self._get_embedding(new_nl_query)
                    if embedding_array is not None:
                        old_embedding = cache_entry.embedding
                        cache_entry.embedding = embedding_array
                        changes.append(("embedding", old_embedding, embedding_array))
                    changes.append(("nl_query", cache_entry.nl_query, new_nl_query))

            # Apply other updates
            for field, new_value in updates.items():
                if hasattr(cache_entry, field):
                    old_value = getattr(cache_entry, field)
                    if old_value != new_value:
                        setattr(cache_entry, field, new_value)
                        changes.append((field, old_value, new_value))

            # Update the updated_at timestamp
            cache_entry.updated_at = datetime.datetime.utcnow()

            # Commit the changes
            self.session.commit()

            # Log changes to audit log if there are any
            if changes:
                for field, old_val, new_val in changes:
                    audit_log = CacheAuditLog(
                        cache_entry_id=cache_entry.id,
                        changed_field=field,
                        old_value=old_val,
                        new_value=new_val,
                        change_reason=change_reason,
                        changed_by=changed_by
                    )
                    self.session.add(audit_log)
                self.session.commit()

            logger.info(f"Updated cache entry with ID {query_id}")
            return cache_entry.to_dict()

        except SQLAlchemyError as e:
            logger.error(f"Database error updating query {query_id}: {str(e)}", exc_info=True)
            self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"Error updating query {query_id}: {str(e)}", exc_info=True)
            self.session.rollback()
            raise ValueError(f"Error updating cache entry: {str(e)}")

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

        # Log search results for debugging
        logger.info(f"Vector search results: distances={distances[0].tolist()}, indices={indices[0].tolist()}")
        logger.info(f"Applying threshold filter: {self.similarity_threshold}")

        return filtered_results

    def get_all_queries(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all cache entries, optionally filtered by status.

        Args:
            status: Optional status to filter by.

        Returns:
            List of cache entry dictionaries.
        """
        query = self.session.query(Text2SQLCache)
        if status:
            query = query.filter(Text2SQLCache.status == status)
        return [entry.to_dict() for entry in query.all()]

    def get_cache_count(self) -> int:
        """Get the total number of cache entries.

        Returns:
            Total count of cache entries.
        """
        return self.session.query(Text2SQLCache).count()

    def get_valid_cache_count(self) -> int:
        """Get the number of cache entries with active status.

        Returns:
            Count of active cache entries.
        """
        return self.session.query(Text2SQLCache).filter(Text2SQLCache.status == 'active').count()

    def get_template_count(self) -> int:
        """Get the number of cache entries that are templates.

        Returns:
            Count of template cache entries.
        """
        return self.session.query(Text2SQLCache).filter(Text2SQLCache.is_template == True).count()

    def get_template_type_counts(self) -> Dict[str, int]:
        """Get counts of cache entries by template type.

        Returns:
            Dictionary mapping template types to their counts.
        """
        type_counts = {}
        for t_type in TemplateType:
            count = self.session.query(Text2SQLCache).filter(Text2SQLCache.template_type == t_type).count()
            type_counts[t_type.value] = count
        return type_counts

    def get_distinct_values(self, field: str) -> List[str]:
        """Get distinct non-null values for a specified field.

        Args:
            field: The field name to get distinct values for (e.g., 'catalog_type').

        Returns:
            List of distinct non-null values for the field.
        """
        return [value for value, in self.session.query(getattr(Text2SQLCache, field)).distinct().all() if value is not None]

    def execute_workflow(
        self, 
        workflow_id: int, 
        entity_values: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow by parsing its JSON structure and processing each step.

        Args:
            workflow_id: The ID of the workflow cache entry to execute.
            entity_values: Optional dictionary of entity values for substitution in steps.

        Returns:
            Dictionary containing the results of the workflow execution.

        Raises:
            ValueError: If the workflow ID is invalid, not a workflow type, or JSON is malformed.
            SQLAlchemyError: If a database error occurs.
        """
        from sqlalchemy.exc import SQLAlchemyError
        import json
        from typing import Dict, Any, Optional

        try:
            # Fetch the workflow cache entry
            workflow_entry = (
                self.session.query(Text2SQLCache)
                .filter(Text2SQLCache.id == workflow_id, Text2SQLCache.is_valid)
                .first()
            )

            if not workflow_entry:
                raise ValueError(f"Workflow with ID {workflow_id} not found or is invalid")

            if workflow_entry.template_type != TemplateType.WORKFLOW:
                raise ValueError(f"Cache entry with ID {workflow_id} is not of type 'workflow'")

            # Parse the JSON template
            try:
                workflow_data = json.loads(workflow_entry.template)
                if not isinstance(workflow_data, dict) or 'steps' not in workflow_data:
                    raise ValueError("Invalid workflow JSON structure: 'steps' key not found")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in workflow template: {str(e)}")

            # Initialize results
            results = {"workflow_id": workflow_id, "steps": []}
            step_results = {}

            # Process steps
            steps = workflow_data.get('steps', [])
            if not steps:
                return {"workflow_id": workflow_id, "steps": [], "message": "No steps defined in workflow"}

            # Group steps by execution type for parallel processing (simplified for now)
            sequential_steps = [step for step in steps if step.get('type') == 'sequential']
            parallel_steps = [step for step in steps if step.get('type') == 'parallel']

            # Execute sequential steps
            for step in sequential_steps:
                step_result = self._execute_workflow_step(step, entity_values, step_results)
                step_results[step.get('cache_id')] = step_result
                results['steps'].append(step_result)

            # Execute parallel steps (simplified as sequential for now, could use threading/async in future)
            for step in parallel_steps:
                step_result = self._execute_workflow_step(step, entity_values, step_results)
                step_results[step.get('cache_id')] = step_result
                results['steps'].append(step_result)

            # Increment usage count for workflow
            workflow_entry.usage_count = (workflow_entry.usage_count or 0) + 1
            self.session.commit()

            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error executing workflow: {str(e)}", exc_info=True)
            self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to execute workflow: {str(e)}")

    def _execute_workflow_step(
        self, 
        step: Dict[str, Any], 
        entity_values: Optional[Dict[str, Any]], 
        previous_results: Dict[int, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single step in a workflow by fetching the referenced cache entry and processing it.

        Args:
            step: Dictionary containing step details (cache_id, type, description).
            entity_values: Optional entity values for substitution.
            previous_results: Results from previous steps for potential data passing.

        Returns:
            Dictionary with the result of the step execution.
        """
        cache_id = step.get('cache_id')
        if not isinstance(cache_id, int):
            return {"step": step, "status": "error", "message": "Invalid cache_id in step"}

        try:
            # Fetch the cache entry for this step
            cache_entry = (
                self.session.query(Text2SQLCache)
                .filter(Text2SQLCache.id == cache_id, Text2SQLCache.is_valid)
                .first()
            )

            if not cache_entry:
                return {"step": step, "status": "error", "message": f"Cache entry with ID {cache_id} not found or invalid"}

            # Increment usage count for the step's cache entry
            cache_entry.usage_count = (cache_entry.usage_count or 0) + 1

            # Handle entity substitution if needed
            substituted_template = cache_entry.template
            if cache_entry.is_template and entity_values:
                if cache_entry.entity_replacements:
                    from .entity_substitution import Text2SQLEntitySubstitution
                    substituted_template, mapping = Text2SQLEntitySubstitution.extract_and_replace_entities(
                        nl_query="",
                        template=cache_entry.template,
                        entity_replacements=cache_entry.entity_replacements,
                        new_entity_values=entity_values,
                        template_type=cache_entry.template_type
                    )
                else:
                    return {"step": step, "status": "error", "message": "Entity substitution needed but no replacements defined"}

            # Simplified execution: return the substituted template as result
            # In a full implementation, this could execute SQL, call APIs, etc.
            result = {
                "step": step,
                "status": "success",
                "cache_id": cache_id,
                "template_type": cache_entry.template_type,
                "result": substituted_template
            }

            # Commit usage count update
            self.session.commit()

            return result

        except Exception as e:
            logger.error(f"Error executing step for cache_id {cache_id}: {str(e)}", exc_info=True)
            return {"step": step, "status": "error", "message": str(e)}

    def change_status(self, query_id: int, new_status: str, reason: Optional[str] = None, changed_by: Optional[str] = None) -> bool:
        """
        Change the status of a cache entry.

        Args:
            query_id: ID of the query to update.
            new_status: New status for the cache entry (pending, active, archive).
            reason: Optional reason for the status change.
            changed_by: Optional identifier of who made the change.

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

            old_status = query.status
            if old_status != new_status:
                query.status = new_status
                query.updated_at = datetime.datetime.utcnow()

                # Log the status change in audit log
                audit_log = CacheAuditLog(
                    cache_entry_id=query_id,
                    changed_field="status",
                    old_value=old_status,
                    new_value=new_status,
                    change_reason=reason,
                    changed_by=changed_by
                )
                self.session.add(audit_log)

                self.session.commit()
                logger.info(f"Changed status of cache entry with ID {query_id} to {new_status}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to change status of query {query_id}: {str(e)}", exc_info=True
            )
            self.session.rollback()
            raise

    def process_completion(
        self,
        query: str,
        similarity_threshold: float = 0.85,
        use_llm: bool = False,
        catalog_type: Optional[str] = None,
        catalog_subtype: Optional[str] = None,
        catalog_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a completion request using the NL cache.

        Args:
            query: The natural language query to process.
            similarity_threshold: The similarity threshold for cache matching.
            use_llm: If True, use LLM to enhance search results with semantic analysis.
            catalog_type: Optional catalog type to filter cache entries.
            catalog_subtype: Optional catalog subtype to filter cache entries.
            catalog_name: Optional catalog name to filter cache entries.

        Returns:
            A dictionary containing the completion result and metadata.
        """
        entity_sub = Text2SQLEntitySubstitution()
        response_data = {}
        final_result = ""
        cache_hit = False
        similarity_score = 0.0
        explanation = None

        # Get multiple results to allow LLM to choose from them if use_llm is enabled
        limit = 5 if use_llm else 1
        cache_results = self.search_query(
            nl_query=query,
            similarity_threshold=similarity_threshold,
            limit=limit,
            catalog_type=catalog_type,
            catalog_subtype=catalog_subtype,
            catalog_name=catalog_name
        )

        if not cache_results or len(cache_results) == 0:
            logger.info(f"No cache matches for query: {query[:50]}...")
            response_data = {
                "cache_template": "No cached template found for this query.",
                "cache_hit": False,
                "similarity_score": 0.0,
                "template_id": None,
                "cached_query": None,
                "user_query": query,
                "updated_template": None,
                "llm_explanation": "No similar query found in cache.",
            }
        else:
            updated_query = None
            if use_llm and len(cache_results) > 0:
                if not LLMService or not LLMService.is_configured():
                    logger.warning("LLM enhancement requested but service not configured")
                    response_data = {
                        "warning": "LLM enhancement was requested but the service is not configured. Set OPENROUTER_API_KEY in .env file.",
                    }
                    best_match = cache_results[0]
                    similarity_score = best_match.get("similarity", 0.0)
                else:
                    try:
                        logger.info(f"Using LLM enhancement for query: {query[:50]}...")
                        llm_service = LLMService(model=os.getenv("OPENROUTER_MODEL", "google/gemini-pro"))
                        llm_result = llm_service.can_answer_with_context(
                            query=query,
                            context_entries=cache_results,
                            similarity_threshold=similarity_threshold
                        )

                        can_answer = llm_result.get("can_answer", False)
                        explanation = llm_result.get("explanation", "")
                        selected_entry_id = llm_result.get("selected_entry_id")
                        updated_query = llm_result.get("updated_query")

                        if can_answer and selected_entry_id:
                            selected_entry = next(
                                (entry for entry in cache_results if entry.get("id") == selected_entry_id),
                                None
                            )
                            if selected_entry:
                                best_match = selected_entry
                                similarity_score = selected_entry.get("similarity", 0.0)
                                logger.info(
                                    f"LLM selected cache entry: {selected_entry_id} for query: {query[:50]}..."
                                )
                            else:
                                best_match = cache_results[0]
                                similarity_score = best_match.get("similarity", 0.0)
                        else:
                            best_match = cache_results[0]
                            similarity_score = best_match.get("similarity", 0.0)
                    except Exception as e:
                        logger.error(f"LLM processing failed: {e}", exc_info=True)
                        best_match = cache_results[0]
                        similarity_score = best_match.get("similarity", 0.0)
            else:
                best_match = cache_results[0]
                similarity_score = best_match.get("similarity", 0.0)

            cache_hit = True
            logger.info(
                f"Cache hit for query: {query[:50]}... (score: {similarity_score:.4f})"
            )

            if updated_query:
                logger.info(f"Updated query from LLM: {updated_query}")

            template_id = best_match.get("id")
            template = best_match.get("template", "")
            is_template = best_match.get("is_template", False)

            if is_template:
                try:
                    extraction_query = updated_query if updated_query else query
                    extracted_entities = entity_sub.extract_entities(
                        extraction_query, best_match.get("entity_replacements", {})
                    )

                    substitution_result = self.apply_entity_substitution(
                        template_id=template_id,
                        new_entity_values=extracted_entities,
                    )

                    final_result = substitution_result.get("substituted_template", template)
                    logger.debug(f"Applied entity substitution. Result: {final_result[:50]}...")
                except Exception as e:
                    logger.error(f"Entity substitution failed: {e}", exc_info=True)
                    final_result = template
                    logger.warning(f"Falling back to raw template: {template[:50]}...")
            else:
                final_result = template

        if cache_hit:
            response_data = {
                "cache_template": final_result,
                "cache_hit": True,
                "similarity_score": similarity_score,
                "template_id": template_id,
                "cached_query": best_match.get("nl_query", ""),
                "user_query": query,
                "updated_template": updated_query if updated_query else final_result,
                "llm_explanation": explanation if explanation else "Retrieved from cache based on similarity.",
            }
        else:
            response_data = {
                "cache_template": "No cached template found for this query.",
                "cache_hit": False,
                "similarity_score": 0.0,
                "template_id": None,
                "cached_query": None,
                "user_query": query,
                "updated_template": None,
                "llm_explanation": "No similar query found in cache.",
            }

        try:
            template_id = None
            if cache_hit and 'best_match' in locals():
                template_id = best_match.get("id")

            usage_log = UsageLog(
                cache_entry_id=template_id,
                prompt=query,
                timestamp=datetime.datetime.utcnow(),
                success_status=cache_hit,
                similarity_score=similarity_score if cache_hit else 0.0,
                error_message=None,
                catalog_type=catalog_type,
                catalog_subtype=catalog_subtype,
                catalog_name=catalog_name,
                llm_used=use_llm
            )
            self.session.add(usage_log)
            self.session.commit()
        except Exception as log_error:
            logger.warning(f"Failed to log cache usage with details: {log_error}")
            try:
                self.session.rollback()
            except:
                pass

        return response_data
