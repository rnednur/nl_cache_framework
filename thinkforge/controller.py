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

# Set up logger first
logger = logging.getLogger(__name__)

# Import LLM service for enhanced completions
try:
    from llm_service import LLMService
    logger.info(f"=== LLM SERVICE IMPORT DEBUG ===")
    logger.info(f"LLMService imported successfully: {LLMService is not None}")
    if LLMService:
        logger.info(f"OPENROUTER_API_KEY exists: {bool(os.getenv('OPENROUTER_API_KEY'))}")
        logger.info(f"OPENROUTER_MODEL: {os.getenv('OPENROUTER_MODEL', 'not set')}")
        logger.info(f"LLMService.is_configured(): {LLMService.is_configured()}")
except ImportError as e:
    logger.error(f"Failed to import LLMService: {e}")
    LLMService = None


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
        
        # Initialize LLM service for enhanced workflow execution
        try:
            if LLMService and LLMService.is_configured():
                self.llm_service = LLMService()
                logger.info("LLM service initialized successfully for workflow execution")
            else:
                self.llm_service = None
                logger.info("LLM service not available, workflow execution will use fallback methods")
        except Exception as e:
            logger.warning(f"Failed to initialize LLM service: {e}")
            self.llm_service = None
        
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
        tags: Optional[Dict[str, List[str]]] = None,
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
            tags: Optional dictionary of tags for categorization.
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
            # Handle comma-separated template types
            if ',' in template_type:
                template_types = [t.strip() for t in template_type.split(',')]
                query = query.filter(Text2SQLCache.template_type.in_(template_types))
            else:
                query = query.filter(Text2SQLCache.template_type == template_type)
        if catalog_type:
            # Include entries with matching catalog_type OR where catalog_type is NULL
            from sqlalchemy import or_
            query = query.filter(or_(
                Text2SQLCache.catalog_type == catalog_type,
                Text2SQLCache.catalog_type == None
            ))
        if catalog_subtype:
            # Include entries with matching catalog_subtype OR where catalog_subtype is NULL
            from sqlalchemy import or_
            query = query.filter(or_(
                Text2SQLCache.catalog_subtype == catalog_subtype,
                Text2SQLCache.catalog_subtype == None
            ))
        if catalog_name:
            # Include entries with matching catalog_name OR where catalog_name is NULL
            from sqlalchemy import or_
            query = query.filter(or_(
                Text2SQLCache.catalog_name == catalog_name,
                Text2SQLCache.catalog_name == None
            ))

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
                        # Don't add embedding changes to the audit log as they're too large and cause serialization issues
                    changes.append(("nl_query", cache_entry.nl_query, new_nl_query))

            # Apply other updates
            for field, new_value in updates.items():
                if hasattr(cache_entry, field) and field != "embedding":
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
                    # Skip embedding field to prevent serialization issues
                    if field == "embedding":
                        continue
                        
                    # Convert numpy arrays to lists if encountered
                    if isinstance(old_val, np.ndarray):
                        old_val = "numpy_array_data"  # Just store a placeholder instead of actual data
                    if isinstance(new_val, np.ndarray):
                        new_val = "numpy_array_data"  # Just store a placeholder instead of actual data
                        
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
                    Text2SQLCache.status == Status.ACTIVE
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
            tags: List of tags to search for in format "name:value". If no colon is present,
                 it will search for the tag name in all keys.
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
                Text2SQLCache.status == Status.ACTIVE
            )
            if template_type:
                base_query = base_query.filter(
                    Text2SQLCache.template_type == template_type
                )

            # Fetch all potential candidates first
            candidate_entries = base_query.all()

            results = []
            
            # Parse the search tags into name-value pairs
            parsed_search_tags = []
            for tag in tags:
                if ':' in tag:
                    name, value = tag.split(':', 1)
                    parsed_search_tags.append((name, value))
                else:
                    # If no colon, search for this as a key name
                    parsed_search_tags.append((tag, None))

            for entry in candidate_entries:
                entry_tags = entry.tags or {}  # entry.tags should be a dict
                
                if not isinstance(entry_tags, dict):
                    logger.warning(
                        f"Tags field for entry ID {entry.id} is not a dict: {type(entry.tags)}. Skipping tag match."
                    )
                    continue
                
                # Check if the entry matches the required tags
                matches = []
                
                for tag_name, tag_value in parsed_search_tags:
                    if tag_value is None:
                        # Just look for the tag name as a key
                        tag_match = tag_name in entry_tags
                    else:
                        # Look for the value in the list for this tag name
                        tag_match = tag_name in entry_tags and tag_value in entry_tags.get(tag_name, [])
                    
                    matches.append(tag_match)
                
                # Determine if this entry should be included based on match_all
                if match_all and all(matches):
                    results.append(entry.to_dict())
                elif not match_all and any(matches):
                    results.append(entry.to_dict())

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
                .filter(Text2SQLCache.id == template_id, Text2SQLCache.status == Status.ACTIVE)
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
                .filter(Text2SQLCache.id == workflow_id, Text2SQLCache.status == Status.ACTIVE)
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
        Execute a single step in a workflow using hybrid approach:
        1. Primary: Direct ID-based lookup for exact matches
        2. Secondary: Semantic search fallback for variations
        3. Tertiary: LLM-enhanced step selection and completion

        Args:
            step: Dictionary containing step details (cache_id, type, description, name).
            entity_values: Optional entity values for substitution.
            previous_results: Results from previous steps for potential data passing.

        Returns:
            Dictionary with the result of the step execution.
        """
        cache_id = step.get('cache_id')
        step_description = step.get('description') or step.get('name', '')
        step_type = step.get('type')
        
        # Primary: Direct ID-based lookup (fastest and most reliable)
        if cache_id and isinstance(cache_id, int):
            cache_entry = self._get_cache_entry_by_id(cache_id)
            if cache_entry:
                logger.info(f"Cache hit for step {step_description} using direct ID lookup")
                return self._execute_cache_entry(cache_entry, step, entity_values)
            else:
                logger.warning(f"Cache entry with ID {cache_id} not found, falling back to semantic search")
        
        # Secondary: Semantic search fallback
        if step_description:
            logger.info(f"Attempting semantic search for step: {step_description}")
            similar_entries = self.search_query(
                nl_query=step_description,
                template_type=step_type,
                similarity_threshold=0.85,  # High threshold for workflow steps
                limit=5,
                catalog_type=step.get('catalog_type'),
                catalog_subtype=step.get('catalog_subtype'),
                catalog_name=step.get('catalog_name')
            )
            
            if similar_entries:
                logger.info(f"Found {len(similar_entries)} similar entries for step: {step_description}")
                
                # Use LLM to select best match if available
                best_match = self._llm_select_best_match(
                    step_description, 
                    similar_entries, 
                    step_context=step,
                    previous_results=previous_results
                )
                
                if best_match:
                    logger.info(f"LLM selected best match for step: {step_description}")
                    return self._execute_cache_entry(best_match, step, entity_values)
                else:
                    # Fallback to highest similarity match
                    best_match = similar_entries[0]
                    logger.info(f"Using highest similarity match for step: {step_description}")
                    return self._execute_cache_entry(best_match, step, entity_values)
        
        # Tertiary: LLM completion for missing steps
        logger.info(f"No suitable cache entry found for step: {step_description}, attempting LLM completion")
        return self._llm_complete_step(step, entity_values, previous_results)

    def _get_cache_entry_by_id(self, cache_id: int) -> Optional[Text2SQLCache]:
        """
        Get a cache entry by ID with status validation.
        
        Args:
            cache_id: The ID of the cache entry to retrieve.
            
        Returns:
            The cache entry if found and active, None otherwise.
        """
        try:
            cache_entry = (
                self.session.query(Text2SQLCache)
                .filter(Text2SQLCache.id == cache_id, Text2SQLCache.status == Status.ACTIVE)
                .first()
            )
            return cache_entry
        except Exception as e:
            logger.error(f"Error fetching cache entry by ID {cache_id}: {str(e)}")
            return None

    def _execute_cache_entry(
        self, 
        cache_entry: Text2SQLCache, 
        step: Dict[str, Any], 
        entity_values: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute a cache entry with entity substitution and usage tracking.
        
        Args:
            cache_entry: The cache entry to execute.
            step: The workflow step details.
            entity_values: Optional entity values for substitution.
            
        Returns:
            Dictionary with the execution result.
        """
        try:
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
                    return {
                        "step": step, 
                        "status": "error", 
                        "message": "Entity substitution needed but no replacements defined"
                    }

            # Simplified execution: return the substituted template as result
            # In a full implementation, this could execute SQL, call APIs, etc.
            result = {
                "step": step,
                "status": "success",
                "cache_id": cache_entry.id,
                "template_type": cache_entry.template_type,
                "result": substituted_template,
                "execution_method": "cache_entry_execution"
            }

            # Commit usage count update
            self.session.commit()

            return result

        except Exception as e:
            logger.error(f"Error executing cache entry {cache_entry.id}: {str(e)}", exc_info=True)
            return {"step": step, "status": "error", "message": str(e)}

    def _llm_select_best_match(
        self, 
        step_description: str, 
        similar_entries: List[Dict[str, Any]], 
        step_context: Dict[str, Any],
        previous_results: Dict[int, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to select the best matching cache entry for a workflow step.
        
        Args:
            step_description: Description of the step to match.
            similar_entries: List of similar cache entries.
            step_context: Additional context about the step.
            previous_results: Results from previous steps.
            
        Returns:
            The best matching cache entry or None if no good match.
        """
        try:
            # Check if LLM service is available
            if not hasattr(self, 'llm_service') or not self.llm_service:
                logger.info("LLM service not available, using highest similarity match")
                return similar_entries[0] if similar_entries else None
            
            # Prepare context for LLM selection
            context = {
                "step_description": step_description,
                "step_type": step_context.get('type'),
                "step_position": step_context.get('position'),
                "previous_steps": list(previous_results.keys()) if previous_results else [],
                "candidates": [
                    {
                        "id": entry.get("id"),
                        "nl_query": entry.get("nl_query"),
                        "template_type": entry.get("template_type"),
                        "similarity": entry.get("similarity", 0.0),
                        "catalog_type": entry.get("catalog_type"),
                        "tags": entry.get("tags", {})
                    }
                    for entry in similar_entries[:3]  # Limit to top 3 for LLM analysis
                ]
            }
            
            # Create prompt for LLM selection
            prompt = f"""
            Select the best cache entry for this workflow step:
            
            Step Description: {step_description}
            Step Type: {step_context.get('type', 'unknown')}
            Step Position: {step_context.get('position', 'unknown')}
            
            Available candidates:
            {chr(10).join([f"- ID {c['id']}: {c['nl_query']} (similarity: {c['similarity']:.3f}, type: {c['template_type']})" for c in context['candidates']])}
            
            Previous steps completed: {len(context['previous_steps'])}
            
            Select the best match by ID number. Consider:
            1. Semantic similarity to step description
            2. Template type compatibility
            3. Position in workflow sequence
            4. Previous step context
            
            Return only the ID number of the best match, or 'none' if no good match exists.
            """
            
            # Get LLM response
            response = self.llm_service.generate_text(prompt, max_tokens=10)
            selected_id = response.strip()
            
            # Parse LLM response
            if selected_id.isdigit():
                selected_entry = next(
                    (entry for entry in similar_entries if entry.get("id") == int(selected_id)), 
                    None
                )
                if selected_entry:
                    logger.info(f"LLM selected cache entry {selected_id} for step: {step_description}")
                    return selected_entry
            
            logger.info(f"LLM could not determine best match for step: {step_description}")
            return None
            
        except Exception as e:
            logger.error(f"Error in LLM step selection: {str(e)}")
            # Fallback to highest similarity
            return similar_entries[0] if similar_entries else None

    def _llm_complete_step(
        self, 
        step: Dict[str, Any], 
        entity_values: Optional[Dict[str, Any]], 
        previous_results: Dict[int, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to complete a step when no suitable cache entry is found.
        
        Args:
            step: The workflow step details.
            entity_values: Optional entity values for substitution.
            previous_results: Results from previous steps.
            
        Returns:
            Dictionary with the LLM-generated step result.
        """
        try:
            step_description = step.get('description') or step.get('name', 'Unknown step')
            
            # Check if LLM service is available
            if not hasattr(self, 'llm_service') or not self.llm_service:
                return {
                    "step": step,
                    "status": "error", 
                    "message": f"No suitable cache entry found for step: {step_description}. LLM service not available for completion."
                }
            
            # Create completion prompt
            prompt = f"""
            Complete this workflow step: {step_description}
            
            Step Type: {step.get('type', 'unknown')}
            Step Position: {step.get('position', 'unknown')}
            
            Previous step results: {len(previous_results)} steps completed
            
            Generate a template or action that would fulfill this step.
            Consider the step type and any dependencies from previous steps.
            
            Return a JSON object with:
            - template: The generated template/action
            - explanation: Brief explanation of what this step does
            - dependencies: List of any dependencies from previous steps
            """
            
            # Get LLM response
            response = self.llm_service.generate_text(prompt, max_tokens=200)
            
            try:
                # Parse LLM response
                llm_result = json.loads(response)
                template = llm_result.get('template', 'LLM-generated template')
                explanation = llm_result.get('explanation', 'Generated by LLM')
                
                return {
                    "step": step,
                    "status": "success",
                    "cache_id": None,
                    "template_type": step.get('type', 'llm_generated'),
                    "result": template,
                    "execution_method": "llm_completion",
                    "llm_explanation": explanation,
                    "warning": "This step was completed using LLM generation, not from cache"
                }
                
            except json.JSONDecodeError:
                # Fallback if LLM response isn't valid JSON
                return {
                    "step": step,
                    "status": "success",
                    "cache_id": None,
                    "template_type": step.get('type', 'llm_generated'),
                    "result": response,
                    "execution_method": "llm_completion",
                    "llm_explanation": "Generated by LLM (raw response)",
                    "warning": "This step was completed using LLM generation, not from cache"
                }
                
        except Exception as e:
            logger.error(f"Error in LLM step completion: {str(e)}")
            return {
                "step": step,
                "status": "error",
                "message": f"Failed to complete step '{step.get('description', 'Unknown')}' using LLM: {str(e)}"
            }

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
        similarity_threshold: Optional[float] = None,
        use_llm: bool = False,
        catalog_type: Optional[str] = None,
        catalog_subtype: Optional[str] = None,
        catalog_name: Optional[str] = None,
        template_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process a completion request using the NL cache.

        Args:
            query: The natural language query to process.
            similarity_threshold: The similarity threshold for cache matching.
            use_llm: If True, use LLM to enhance search results with semantic analysis.
            catalog_type: Optional catalog type to filter cache entries.
            catalog_subtype: Optional catalog subtype to filter cache entries.
            catalog_name: Optional catalog name to filter cache entries.
            template_type: Optional template type to filter cache entries and customize prompting.
            limit: Optional number of top similarity results to use, defaults to 5 if use_llm is True, 1 otherwise.

        Returns:
            A dictionary containing the completion result and metadata.
        """
        # DEBUG: Log the input parameters
        logger.info(f"=== PROCESS_COMPLETION DEBUG ===")
        logger.info(f"Query: {query[:100]}...")
        logger.info(f"use_llm parameter: {use_llm} (type: {type(use_llm)})")
        logger.info(f"similarity_threshold: {similarity_threshold}")
        logger.info(f"template_type: {template_type}")
        logger.info(f"limit: {limit}")
        logger.info(f"LLMService available: {LLMService is not None}")
        if LLMService:
            logger.info(f"LLMService configured: {LLMService.is_configured()}")
        
        # Set default similarity threshold if not provided
        if similarity_threshold is None:
            similarity_threshold = 0.85  # Default fallback value
            logger.info(f"similarity_threshold was None, using default: {similarity_threshold}")
        
        entity_sub = Text2SQLEntitySubstitution()
        response_data = {}
        final_result = ""
        cache_hit = False
        similarity_score = 0.0
        explanation = None

        # Get multiple results to allow LLM to choose from them if use_llm is enabled
        # Use the provided limit or default to 5 if use_llm is True, 1 otherwise
        search_limit = limit if limit is not None else (5 if use_llm else 1)
        cache_results = self.search_query(
            nl_query=query,
            template_type=template_type,
            similarity_threshold=similarity_threshold,
            limit=search_limit,
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
                "considered_entries": [],
                "is_confident": False
            }
        else:
            updated_query = None
            is_confident = True  # Default confidence level
            if use_llm and len(cache_results) > 0:
                logger.info(f"=== LLM PROCESSING STARTED ===")
                logger.info(f"use_llm is True, cache_results count: {len(cache_results)}")
                if not LLMService or not LLMService.is_configured():
                    logger.warning("LLM enhancement requested but service not configured")
                    logger.info(f"LLMService exists: {LLMService is not None}")
                    if LLMService:
                        logger.info(f"LLMService is_configured: {LLMService.is_configured()}")
                    response_data = {
                        "warning": "LLM enhancement was requested but the service is not configured. Set OPENROUTER_API_KEY in .env file.",
                    }
                    best_match = cache_results[0]
                    similarity_score = best_match.get("similarity", 0.0)
                else:
                    try:
                        logger.info(f"Using LLM enhancement for query: {query[:50]}...")
                        logger.info(f"Creating LLMService with model: {os.getenv('OPENROUTER_MODEL', 'google/gemini-pro')}")
                        llm_service = LLMService(model=os.getenv("OPENROUTER_MODEL", "google/gemini-pro"))
                        
                        # Create template-specific context for better LLM understanding
                        template_context = self._get_template_specific_context(template_type, query)
                        logger.info(f"Using template-specific context for type: {template_type}")
                        
                        logger.info(f"Calling can_answer_with_context with {len(cache_results)} entries")
                        llm_result = llm_service.can_answer_with_context(
                            query=query,
                            context_entries=cache_results,
                            similarity_threshold=similarity_threshold,
                            additional_context=template_context
                        )
                        logger.info(f"LLM result received: {llm_result}")

                        can_answer = llm_result.get("can_answer", False)
                        explanation = llm_result.get("explanation", "")
                        selected_entry_id = llm_result.get("selected_entry_id")
                        updated_query = llm_result.get("updated_query")
                        
                        logger.info(f"LLM analysis: can_answer={can_answer}, selected_entry_id={selected_entry_id}")
                        
                        # Set confidence based on LLM's assessment
                        is_confident = can_answer

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
                                logger.warning(f"LLM selected entry {selected_entry_id} not found in cache_results, using first result")
                        else:
                            best_match = cache_results[0]
                            similarity_score = best_match.get("similarity", 0.0)
                            logger.info(f"LLM determined it cannot answer or no entry selected, using first result")
                    except Exception as e:
                        logger.error(f"LLM processing failed: {e}", exc_info=True)
                        best_match = cache_results[0]
                        similarity_score = best_match.get("similarity", 0.0)
            else:
                logger.info(f"=== NO LLM PROCESSING ===")
                logger.info(f"use_llm: {use_llm}, cache_results count: {len(cache_results) if cache_results else 0}")
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
            template_type = best_match.get("template_type", "")

            # Handle entity substitution for templates with explicit placeholders
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
            
            # Handle LLM-based workflow adaptation for workflow templates
            elif template_type == "workflow" or self._is_workflow_template(template):
                try:
                    original_query = best_match.get("nl_query", "")
                    current_query = updated_query if updated_query else query
                    
                    logger.info(f"Detected workflow template (type: {template_type})")
                    logger.info(f"Attempting LLM-based workflow adaptation:")
                    logger.info(f"  Original query: {original_query}")
                    logger.info(f"  Current query: {current_query}")
                    
                    # Apply LLM-based workflow adaptation if queries are different
                    # Handle case where current_query might be the original user query string
                    current_query_str = current_query if isinstance(current_query, str) else query
                    if original_query.lower() != current_query_str.lower() and self.llm_service:
                        logger.info(f"Queries are different, adapting workflow with LLM")
                        final_result = self._adapt_workflow_with_llm(
                            template, original_query, current_query_str
                        )
                        logger.info(f"LLM workflow adaptation completed successfully")
                    else:
                        final_result = template
                        if original_query.lower() == current_query_str.lower():
                            logger.info(f"Queries are identical, no adaptation needed")
                        else:
                            logger.info(f"LLM not available, using original template")
                    
                    logger.debug(f"Result preview: {final_result[:200]}...")
                    
                except Exception as e:
                    logger.error(f"LLM workflow adaptation failed: {e}", exc_info=True)
                    final_result = template
                    logger.warning(f"Falling back to original workflow template")
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
                "considered_entries": [entry.get("id") for entry in cache_results],
                "is_confident": is_confident
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
                "considered_entries": [],
                "is_confident": False
            }

        try:
            template_id = None
            if cache_hit and 'best_match' in locals():
                template_id = best_match.get("id")

            # Determine the response to log
            logged_response = None
            if cache_hit:
                logged_response = response_data.get("updated_template") or response_data.get("cache_template")

            # Get considered entries for logging
            considered_entry_ids = response_data.get("considered_entries", [])

            # Ensure response is a string for database storage
            response_for_log = updated_query if updated_query else final_result
            if isinstance(response_for_log, dict):
                import json
                response_for_log = json.dumps(response_for_log)
            elif not isinstance(response_for_log, str):
                response_for_log = str(response_for_log)
                
            usage_log = UsageLog(
                cache_entry_id=template_id,
                prompt=query,
                response=response_for_log,
                timestamp=datetime.datetime.utcnow(),
                success_status=cache_hit,
                similarity_score=similarity_score if cache_hit else 0.0,
                error_message=None,
                catalog_type=catalog_type,
                catalog_subtype=catalog_subtype,
                catalog_name=catalog_name,
                llm_used=use_llm,
                considered_entries=considered_entry_ids,
                is_confident=response_data.get("is_confident", None)
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

    def design_workflow_with_llm(
        self,
        nl_query: str,
        compatible_entries: List[Dict[str, Any]],
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to design a workflow based on a natural language query and available cache entries.
        Enhanced with execution context for better workflow planning.
        
        Args:
            nl_query: The natural language query to analyze
            compatible_entries: List of available cache entries to use as steps
            execution_context: Optional execution context (database configs, API endpoints, etc.)
            
        Returns:
            Dictionary containing workflow nodes, edges, compiled template, and execution plan
        """
        import random
        from typing import List, Dict, Any
        
        try:
            logger.info(f"Designing workflow for query: {nl_query}")
            logger.info(f"Available cache entries: {len(compatible_entries)}")
            logger.info(f"Execution context provided: {execution_context is not None}")
            
            # Initialize LLM service
            from backend.llm_service import LLMService
            llm_service = LLMService()
            
            # Enhance workflow design with execution context
            enhanced_compatible_entries = self._enhance_entries_with_execution_context(
                compatible_entries, execution_context
            )
            
            # Generate workflow using LLM service with execution context
            workflow_design = llm_service.generate_workflow_with_execution_context(
                nl_query, enhanced_compatible_entries, execution_context
            )
            
            # Convert the workflow design to ReactFlow nodes and edges
            reactflow_design = self._convert_to_reactflow_format(workflow_design)
            
            # Compile the workflow template from nodes and edges (final executable format)
            from thinkforge.workflow_compiler import compile_workflow_template
            workflow_template = compile_workflow_template(reactflow_design["nodes"], reactflow_design["edges"])
            
            # Generate execution plan with resource requirements
            execution_plan = self._generate_execution_plan(workflow_template, execution_context)
            
            # Build final response
            response = {
                "nodes": reactflow_design["nodes"],
                "edges": reactflow_design["edges"],
                "workflow_template": workflow_template,
                "execution_plan": execution_plan,
                "explanation": workflow_design.get("explanation", ""),
                "estimated_duration": execution_plan.get("estimated_duration"),
                "resource_requirements": execution_plan.get("resource_requirements")
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error designing workflow with LLM: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to design workflow: {str(e)}")
    
    def _enhance_entries_with_execution_context(
        self,
        compatible_entries: List[Dict[str, Any]],
        execution_context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enhance cache entries with execution context information.
        
        Args:
            compatible_entries: List of cache entries
            execution_context: Execution context
            
        Returns:
            Enhanced cache entries with execution metadata
        """
        if not execution_context:
            return compatible_entries
        
        enhanced_entries = []
        
        for entry in compatible_entries:
            enhanced_entry = entry.copy()
            template_type = entry.get("template_type", "")
            
            # Add execution context based on template type
            if template_type == "sql":
                enhanced_entry["execution_capabilities"] = {
                    "database_types": execution_context.get("available_databases", []),
                    "estimated_performance": self._estimate_sql_performance(entry),
                    "data_sources": execution_context.get("data_sources", [])
                }
            
            elif template_type == "api":
                enhanced_entry["execution_capabilities"] = {
                    "api_availability": self._check_api_availability(entry, execution_context),
                    "rate_limits": execution_context.get("api_rate_limits", {}),
                    "authentication_methods": execution_context.get("auth_methods", [])
                }
            
            elif template_type in ["function", "script"]:
                enhanced_entry["execution_capabilities"] = {
                    "runtime_environment": execution_context.get("runtime_environment", "python3"),
                    "available_libraries": execution_context.get("available_libraries", []),
                    "resource_limits": execution_context.get("resource_limits", {})
                }
            
            # Add general execution metadata
            enhanced_entry["execution_metadata"] = {
                "estimated_duration": self._estimate_execution_duration(entry),
                "complexity_score": self._calculate_complexity_score(entry),
                "resource_requirements": self._estimate_resource_requirements(entry)
            }
            
            enhanced_entries.append(enhanced_entry)
        
        return enhanced_entries
    
    def _estimate_sql_performance(self, entry: Dict[str, Any]) -> str:
        """Estimate SQL query performance based on template analysis."""
        template = entry.get("template", "").lower()
        
        # Simple heuristics for performance estimation
        if "join" in template and template.count("join") > 2:
            return "slow"
        elif "select * from" in template:
            return "medium"
        elif any(keyword in template for keyword in ["aggregate", "group by", "order by"]):
            return "medium"
        else:
            return "fast"
    
    def _check_api_availability(
        self, 
        entry: Dict[str, Any], 
        execution_context: Dict[str, Any]
    ) -> str:
        """Check API availability based on execution context."""
        execution_config = entry.get("execution_config", {})
        base_url = execution_config.get("base_url", "")
        
        # Check if API is in the available APIs list
        available_apis = execution_context.get("available_apis", [])
        
        for api in available_apis:
            if api.get("base_url") == base_url:
                return api.get("status", "unknown")
        
        return "unknown"
    
    def _estimate_execution_duration(self, entry: Dict[str, Any]) -> float:
        """Estimate execution duration in seconds."""
        template_type = entry.get("template_type", "")
        
        # Base estimates by template type
        base_durations = {
            "sql": 2.0,
            "api": 1.5,
            "function": 0.5,
            "script": 3.0,
            "workflow": 10.0,
            "mcp_tool": 2.5
        }
        
        base_duration = base_durations.get(template_type, 1.0)
        
        # Adjust based on template complexity
        template = entry.get("template", "")
        complexity_multiplier = 1.0
        
        if len(template) > 1000:
            complexity_multiplier *= 1.5
        if template_type == "sql" and "join" in template.lower():
            complexity_multiplier *= 1.3
        
        return base_duration * complexity_multiplier
    
    def _calculate_complexity_score(self, entry: Dict[str, Any]) -> int:
        """Calculate complexity score (1-10) for the entry."""
        template = entry.get("template", "")
        template_type = entry.get("template_type", "")
        
        score = 1
        
        # Base score by template type
        type_scores = {
            "function": 3,
            "sql": 2,
            "api": 2,
            "script": 4,
            "workflow": 6,
            "mcp_tool": 3
        }
        
        score = type_scores.get(template_type, 2)
        
        # Adjust based on template characteristics
        if len(template) > 500:
            score += 1
        if len(template) > 1000:
            score += 1
        
        # SQL specific complexity
        if template_type == "sql":
            template_lower = template.lower()
            if template_lower.count("join") > 2:
                score += 2
            if any(keyword in template_lower for keyword in ["subquery", "with", "union"]):
                score += 1
        
        # Function/script specific complexity
        if template_type in ["function", "script"]:
            if "for " in template or "while " in template:
                score += 1
            if "import " in template:
                score += 1
        
        return min(score, 10)
    
    def _estimate_resource_requirements(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate resource requirements for the entry."""
        template_type = entry.get("template_type", "")
        complexity_score = self._calculate_complexity_score(entry)
        
        # Base resource requirements
        base_requirements = {
            "memory_mb": 64,
            "cpu_cores": 1,
            "disk_mb": 10,
            "network_bandwidth_mbps": 1
        }
        
        # Adjust based on template type
        type_multipliers = {
            "sql": {"memory_mb": 2, "cpu_cores": 1.5},
            "api": {"network_bandwidth_mbps": 5},
            "function": {"memory_mb": 1.5, "cpu_cores": 2},
            "script": {"memory_mb": 3, "cpu_cores": 2, "disk_mb": 5},
            "workflow": {"memory_mb": 4, "cpu_cores": 3, "disk_mb": 3}
        }
        
        multipliers = type_multipliers.get(template_type, {})
        
        # Apply multipliers
        for resource, base_value in base_requirements.items():
            multiplier = multipliers.get(resource, 1.0)
            complexity_factor = 1 + (complexity_score - 1) * 0.2  # Scale with complexity
            base_requirements[resource] = int(base_value * multiplier * complexity_factor)
        
        return base_requirements
    
    def _generate_execution_plan(
        self,
        workflow_template: Dict[str, Any],
        execution_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate an execution plan with resource requirements and timing estimates.
        
        Args:
            workflow_template: Compiled workflow template
            execution_context: Execution context
            
        Returns:
            Execution plan with resource requirements and estimates
        """
        steps = workflow_template.get("steps", {})
        execution_plan_groups = workflow_template.get("executionPlan", [])
        
        total_duration = 0.0
        total_resources = {
            "memory_mb": 0,
            "cpu_cores": 0,
            "disk_mb": 0,
            "network_bandwidth_mbps": 0
        }
        
        execution_strategy = []
        
        for group in execution_plan_groups:
            mode = group.get("mode", "sequential")
            step_ids = group.get("steps", [])
            
            group_duration = 0.0
            group_resources = {
                "memory_mb": 0,
                "cpu_cores": 0,
                "disk_mb": 0,
                "network_bandwidth_mbps": 0
            }
            
            for step_id in step_ids:
                step_data = steps.get(step_id, {})
                
                # Get step metadata (would be populated during enhancement)
                metadata = step_data.get("metadata", {})
                execution_metadata = metadata.get("execution_metadata", {})
                
                step_duration = execution_metadata.get("estimated_duration", 1.0)
                step_resources = execution_metadata.get("resource_requirements", {})
                
                if mode == "parallel":
                    # For parallel execution, duration is the max of all steps
                    group_duration = max(group_duration, step_duration)
                    # Resources are additive for parallel execution
                    for resource, value in step_resources.items():
                        group_resources[resource] += value
                else:
                    # For sequential execution, duration is additive
                    group_duration += step_duration
                    # Resources are the max needed at any point
                    for resource, value in step_resources.items():
                        group_resources[resource] = max(group_resources[resource], value)
            
            total_duration += group_duration
            
            # Overall resources are the max needed across all groups
            for resource, value in group_resources.items():
                total_resources[resource] = max(total_resources[resource], value)
            
            execution_strategy.append({
                "group_id": len(execution_strategy) + 1,
                "mode": mode,
                "steps": step_ids,
                "estimated_duration": group_duration,
                "resource_requirements": group_resources
            })
        
        # Add execution context considerations
        if execution_context:
            # Adjust for available resources
            available_resources = execution_context.get("available_resources", {})
            if available_resources:
                for resource, required in total_resources.items():
                    available = available_resources.get(resource, float('inf'))
                    if required > available:
                        logger.warning(f"Required {resource} ({required}) exceeds available ({available})")
        
        return {
            "estimated_duration": total_duration,
            "resource_requirements": total_resources,
            "execution_strategy": execution_strategy,
            "optimization_suggestions": self._generate_optimization_suggestions(
                workflow_template, execution_strategy
            ),
            "execution_readiness": self._assess_execution_readiness(
                workflow_template, execution_context
            )
        }
    
    def _generate_optimization_suggestions(
        self,
        workflow_template: Dict[str, Any],
        execution_strategy: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate optimization suggestions for the workflow."""
        suggestions = []
        
        # Check for parallelization opportunities
        sequential_groups = [g for g in execution_strategy if g["mode"] == "sequential"]
        if len(sequential_groups) > 1:
            suggestions.append("Consider parallelizing independent sequential steps to reduce total execution time")
        
        # Check for resource efficiency
        total_steps = sum(len(g["steps"]) for g in execution_strategy)
        if total_steps > 10:
            suggestions.append("Large workflow detected - consider breaking into smaller sub-workflows")
        
        # Check for long-running steps
        long_steps = [
            g for g in execution_strategy 
            if g.get("estimated_duration", 0) > 30
        ]
        if long_steps:
            suggestions.append("Long-running steps detected - consider adding progress monitoring and timeout handling")
        
        return suggestions
    
    def _assess_execution_readiness(
        self,
        workflow_template: Dict[str, Any],
        execution_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess whether the workflow is ready for execution."""
        readiness = {
            "ready": True,
            "issues": [],
            "warnings": []
        }
        
        steps = workflow_template.get("steps", {})
        
        # Check each step for execution readiness
        for step_id, step_data in steps.items():
            template_type = step_data.get("templateType", "")
            
            # Check for required execution configuration
            execution_config = step_data.get("execution_config", {})
            
            if template_type == "sql" and not execution_config.get("database"):
                readiness["issues"].append(f"Step {step_id}: Missing database configuration")
                readiness["ready"] = False
            
            elif template_type == "api" and not execution_config.get("base_url"):
                readiness["issues"].append(f"Step {step_id}: Missing API base URL")
                readiness["ready"] = False
            
            # Check for missing templates
            if not step_data.get("template"):
                readiness["issues"].append(f"Step {step_id}: Missing template content")
                readiness["ready"] = False
        
        # Check execution context availability
        if execution_context:
            required_capabilities = set()
            for step_data in steps.values():
                template_type = step_data.get("templateType", "")
                required_capabilities.add(template_type)
            
            available_capabilities = set(execution_context.get("available_capabilities", []))
            missing_capabilities = required_capabilities - available_capabilities
            
            if missing_capabilities:
                for capability in missing_capabilities:
                    readiness["warnings"].append(f"Capability '{capability}' may not be available in execution environment")
        
        return readiness
    
    def _create_workflow_design_prompt(self, nl_query: str, cache_entries: List[Dict[str, Any]]) -> str:
        """
        Create a prompt for the LLM to design a workflow based on the query and available entries.
        """
        entries_text = "\n".join([
            f"- ID: {entry['id']}, Name: {entry['nl_query']}, Type: {entry['template_type']}"
            for entry in cache_entries
        ])
        
        prompt = f"""
        You are designing a workflow to solve the following natural language request:
        
        REQUEST: {nl_query}
        
        Available cache entries that can be used as steps in the workflow:
        {entries_text}
        
        Please design a workflow that solves this request by selecting appropriate steps from the
        available cache entries and connecting them in a meaningful sequence. For each step, explain
        how it should be adapted or parameterized to work for this specific request.
        
        Your response should be in JSON format as follows:
        {{
          "steps": [
            {{
              "id": "step1",
              "cache_entry_id": <entry_id>,
              "description": "Description of this step",
              "input_modifications": "Specific modifications or parameters needed for this request",
              "outputs": ["output1", "output2"]
            }},
            ...
          ],
          "connections": [
            {{
              "from": "step1",
              "to": "step2",
              "description": "How output from step1 is used in step2"
            }},
            ...
          ],
          "explanation": "Overall explanation of how this workflow solves the request"
        }}
        
        Focus on selecting the most appropriate steps and creating a logical flow between them.
        """
        
        return prompt
    
    def _parse_workflow_design_response(
        self, 
        llm_response: str, 
        compatible_entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Parse the LLM response and extract the workflow design.
        """
        import json
        import re
        
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'({[\s\S]*})', llm_response)
            if json_match:
                json_str = json_match.group(1)
                workflow_design = json.loads(json_str)
                return workflow_design
            else:
                raise ValueError("Could not extract JSON from LLM response")
                
        except json.JSONDecodeError:
            logger.error(f"Could not parse LLM response as JSON: {llm_response}")
            # Fallback to a simple workflow structure if parsing fails
            return {
                "steps": [],
                "connections": [],
                "explanation": "Failed to parse workflow design from LLM response."
            }
    
    def _convert_to_reactflow_format(self, workflow_design: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert the workflow design to ReactFlow nodes and edges.
        """
        nodes = []
        edges = []
        
        # Add start node
        nodes.append({
            "id": "start",
            "type": "input",
            "data": { "label": "Workflow Start" },
            "position": { "x": 250, "y": 50 }
        })
        
        # Add nodes for each step
        for i, step in enumerate(workflow_design.get("steps", [])):
            node = {
                "id": step.get("id", f"step{i+1}"),
                "type": "default",
                "data": {
                    "label": step.get("description", f"Step {i+1}"),
                    "originalStepId": step.get("cache_entry_id"),
                    "originalStepType": "unknown",  # Would be set from cache entry type
                    "inputModifications": step.get("input_modifications", ""),
                    "outputs": step.get("outputs", [])
                },
                "position": { "x": 250, "y": 150 + (i * 100) }
            }
            nodes.append(node)
        
        # Add edge from start to first step (if any steps exist)
        if workflow_design.get("steps"):
            first_step_id = workflow_design["steps"][0].get("id", "step1")
            edges.append({
                "id": f"start-{first_step_id}",
                "source": "start",
                "target": first_step_id
            })
        
        # Add edges for connections
        for i, connection in enumerate(workflow_design.get("connections", [])):
            edge = {
                "id": f"edge{i+1}",
                "source": connection.get("from"),
                "target": connection.get("to"),
                "data": {
                    "description": connection.get("description", "")
                }
            }
            edges.append(edge)
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def _get_template_specific_context(self, template_type: Optional[str], query: str) -> str:
        """
        Generate template-specific context to guide LLM analysis based on the template type.
        
        Args:
            template_type: The type of template being searched for
            query: The user's query
            
        Returns:
            A context string to help the LLM better understand the domain
        """
        if not template_type:
            return "Focus on finding the most relevant template for the given query."
            
        template_contexts = {
            "sql": """
            The user is looking for SQL query templates. Focus on:
            - Database operations (SELECT, INSERT, UPDATE, DELETE)
            - Data retrieval and manipulation
            - Table joins, filtering, aggregation
            - Consider database schema requirements and SQL syntax
            """,
            
            "api": """
            The user is looking for API endpoint templates. Focus on:
            - REST API calls (GET, POST, PUT, DELETE)
            - API documentation and specifications
            - Request/response formats, headers, parameters
            - HTTP endpoints and web service integrations
            """,
            
            "workflow": """
            The user is looking for workflow automation templates. Focus on:
            - Multi-step processes and automation
            - Task orchestration and sequencing
            - Business process flows and integrations
            - Step-by-step procedures and workflows
            """,
            
            "url": """
            The user is looking for URL/web resource templates. Focus on:
            - Web URLs, links, and endpoints
            - Web page resources and navigation
            - URL patterns and web references
            - Online resources and web services
            """,
            
            "function": """
            The user is looking for function/code templates. Focus on:
            - Programming functions and code snippets
            - Function definitions, parameters, and logic
            - Code implementations and algorithms
            - Programming utilities and methods
            """,
            
            "script": """
            The user is looking for script templates. Focus on:
            - Executable scripts and automation
            - Command-line scripts and tools
            - Batch processing and scripted operations
            - System administration and automation scripts
            """,
            
            "mcp_tool": """
            The user is looking for MCP (Model Context Protocol) tool templates. Focus on:
            - MCP tool integrations and capabilities
            - Tool-based operations and functionality
            - External tool connections and interfaces
            - MCP protocol implementations
            """,
            
            "agent": """
            The user is looking for AI agent templates. Focus on:
            - AI agent configurations and behaviors
            - Agent-based automation and intelligence
            - Autonomous task execution and decision-making
            - Agent workflows and interactions
            """
        }
        
        context = template_contexts.get(template_type.lower(), f"""
            The user is looking for {template_type} templates. Focus on finding content 
            that matches this specific template type and domain.
        """)
        
        return f"""
        TEMPLATE TYPE CONTEXT: {template_type.upper()}
        
        {context.strip()}
        
        When evaluating the cached entries, prioritize templates that best match 
        this template type and the user's specific use case.
        """

    def _adapt_workflow_with_llm(
        self, workflow_template: str, original_query: str, new_query: str
    ) -> str:
        """
        Use LLM to adapt workflow step names and descriptions based on query changes.
        
        Args:
            workflow_template: The original workflow JSON template
            original_query: The original query the workflow was designed for
            new_query: The new query that should be adapted to
            
        Returns:
            Adapted workflow JSON string with updated step names and descriptions
        """
        if not self.llm_service:
            logger.warning("LLM service not available for workflow adaptation")
            return workflow_template
            
        try:
            # Parse workflow to understand structure
            import json
            workflow_data = json.loads(workflow_template)
            
            # Create prompt for LLM to adapt the workflow
            adaptation_prompt = f"""You are an expert at updating JSON-based workflow recipes for data analysis tasks. Your goal is to adapt an existing recipe flow to a new query variation while keeping the structure intact.

Here is the original recipe flow JSON:
{json.dumps(workflow_data, indent=2)}

The original flow is for a query like: "{original_query}".

Now, adapt it to a new query: "{new_query}". Focus on the key changes between the original and new queries. For example:
- Update any phrasing in step names, flow name, or metadata to naturally reflect the new query (e.g., change conditions, counts, types, or descriptors to match while keeping the intent similar).
- Update the flow's "name" field to reflect the new query (e.g., rephrase it to align closely with the new query wording).
- Update step names (e.g., in the "steps" array) to incorporate the new query's elements, ensuring they remain concise and relevant.
- Update the "nl_description" in "metadata" to reflect the new questions, keeping the format like "Fullflow 'Generated Workflow':\\n1) [Updated question 1]\\n2) [Updated question 2]\\n" (adjust numbering if steps change minimally).
- Do not change unrelated fields like IDs, positions, cache_entry_ids, connections, or metadata counts unless they directly conflict with the update.
- Ensure the output is valid JSON.
- If the new query requires adding, removing, or rephrasing steps, only make minimal changes to align with the new query—do not invent entirely new steps or overcomplicate unless the query explicitly demands it. Prioritize keeping the workflow's core logic the same.

Output only the updated JSON object, nothing else."""

            # Call LLM for adaptation
            logger.info(f"Calling LLM for workflow adaptation")
            response = self.llm_service.generate_response(adaptation_prompt)
            
            if not response:
                logger.warning("LLM returned empty response for workflow adaptation")
                return workflow_template
                
            # Extract JSON from response (in case LLM adds extra text)
            adapted_workflow = self._extract_json_from_response(response)
            
            if adapted_workflow:
                logger.info("Successfully adapted workflow with LLM")
                return json.dumps(adapted_workflow, indent=2)
            else:
                logger.warning("Could not extract valid JSON from LLM response")
                return workflow_template
                
        except Exception as e:
            logger.error(f"Error during LLM workflow adaptation: {e}", exc_info=True)
            return workflow_template

    def _extract_json_from_response(self, response: str) -> dict:
        """
        Extract JSON from LLM response, handling cases where LLM might add extra text.
        
        Args:
            response: Raw LLM response that should contain JSON
            
        Returns:
            Parsed JSON dictionary or None if extraction fails
        """
        import json
        
        try:
            # First try parsing the entire response as JSON
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass
            
        # Try to find JSON within the response
        import re
        
        # Look for JSON object patterns
        json_pattern = r'(\{.*\})'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
                
        # Look for JSON starting with specific workflow patterns
        lines = response.split('\n')
        json_started = False
        json_lines = []
        
        for line in lines:
            if not json_started and ('{' in line and ('flow' in line or 'steps' in line)):
                json_started = True
            
            if json_started:
                json_lines.append(line)
                
            # Stop if we find a closing brace at the start of a line (likely end of JSON)
            if json_started and line.strip() == '}':
                break
                
        if json_lines:
            try:
                return json.loads('\n'.join(json_lines))
            except json.JSONDecodeError:
                pass
                
        logger.warning("Could not extract valid JSON from LLM response")
        return None

    def _is_workflow_template(self, template: str) -> bool:
        """
        Check if a template appears to be a workflow based on its structure.
        
        Args:
            template: The template string to check
            
        Returns:
            True if the template appears to be a workflow, False otherwise
        """
        try:
            import json
            data = json.loads(template)
            
            # Check for common workflow structure patterns
            if isinstance(data, dict):
                # Check for workflow indicators
                has_flow = "flow" in data
                has_steps = "steps" in data or (has_flow and "steps" in data.get("flow", {}))
                has_connections = "connections" in data or (has_flow and "connections" in data.get("flow", {}))
                has_metadata = "metadata" in data or (has_flow and "metadata" in data.get("flow", {}))
                
                # If it has steps and either connections or metadata, likely a workflow
                if has_steps and (has_connections or has_metadata):
                    logger.info(f"Template detected as workflow based on structure")
                    return True
                    
            return False
            
        except (json.JSONDecodeError, Exception):
            # If we can't parse as JSON or other error, not a workflow
            return False
