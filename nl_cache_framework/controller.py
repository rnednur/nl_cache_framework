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
from .models import Text2SQLCache, TemplateType, Status, CacheAuditLog
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

        # Get all candidates
        candidates = self.get_all_queries(status=status)
        if not candidates:
            return []

        # Filter by template type and catalog fields if specified
        if template_type or catalog_type or catalog_subtype or catalog_name:
            candidates = [
                c for c in candidates
                if (template_type is None or c.get("template_type") == template_type) and
                   (catalog_type is None or c.get("catalog_type") == catalog_type) and
                   (catalog_subtype is None or c.get("catalog_subtype") == catalog_subtype) and
                   (catalog_name is None or c.get("catalog_name") == catalog_name)
            ]

        # Get embeddings for vector similarity if needed
        candidate_embeddings_list = None
        if search_method in ["vector", "auto"]:
            candidate_texts = [c.get("nl_query", "") for c in candidates]
            if candidate_texts:
                try:
                    candidate_embeddings = self.similarity_util.get_embedding(candidate_texts)
                    if candidate_embeddings is None or len(candidate_embeddings) == 0:
                        logger.warning("Failed to generate embeddings for candidates")
                        candidate_embeddings = None
                    else:
                        # Convert to list of embeddings, ensuring each is a numpy array
                        candidate_embeddings_list = []
                        for emb in candidate_embeddings:
                            if isinstance(emb, np.ndarray):
                                candidate_embeddings_list.append(emb)
                            else:
                                logger.warning("Invalid embedding type in results, using zero vector")
                                candidate_embeddings_list.append(np.zeros(768))
                except Exception as e:
                    logger.error(f"Error generating candidate embeddings: {e}", exc_info=True)
                    candidate_embeddings_list = None
            else:
                logger.warning("No candidate texts to generate embeddings for")

        # Find similar queries
        similar_indices = self.similarity_util.find_most_similar(
            nl_query,
            [c.get("nl_query", "") for c in candidates],
            candidate_embeddings=candidate_embeddings_list,
            method=search_method if search_method in ["vector", "string"] else "vector",
            threshold=similarity_threshold,
        )

        # Return results with similarity scores
        results = []
        for idx, score in similar_indices:
            entry = candidates[idx].copy()
            entry["similarity_score"] = score
            results.append(entry)

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
        Update a query entry.

        Args:
            query_id: ID of the query to update.
            updates: Dictionary of fields to update. Keys should match Text2SQLCache attributes.
                     Special handling for 'nl_query' (recomputes embedding).
            change_reason: Optional reason for the update to log in audit trail.
            changed_by: Optional identifier of who made the change.

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

            # Log changes for audit trail
            audit_logs = []
            for key, value in update_data.items():
                if hasattr(query, key):
                    old_value = getattr(query, key)
                    if old_value != value:
                        audit_logs.append(CacheAuditLog(
                            cache_entry_id=query_id,
                            changed_field=key,
                            old_value=str(old_value) if old_value is not None else None,
                            new_value=str(value) if value is not None else None,
                            change_reason=change_reason,
                            changed_by=changed_by
                        ))
                    # Update the field
                    if key in ['nl_query']: # nl_query already applied if present
                        continue
                    setattr(query, key, value)
                else:
                    logger.warning(
                        f"Attempted to update non-existent attribute '{key}' on Text2SQLCache"
                    )

            # Ensure updated_at is set (handle type change from model)
            query.updated_at = datetime.datetime.utcnow()

            # Add audit logs to session
            self.session.add_all(audit_logs)
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

    def get_all_queries(self, status: Optional[str] = Status.ACTIVE) -> List[Dict[str, Any]]:
        """Get all queries from the cache filtered by status.

        Args:
            status: Optional status to filter by (pending, active, archive). Defaults to ACTIVE.

        Returns:
            List of cache entries as dictionaries matching the status filter.
        """
        try:
            if status:
                queries = (
                    self.session.query(Text2SQLCache)
                    .filter(Text2SQLCache.status == status)
                    .all()
                )
            else:
                queries = self.session.query(Text2SQLCache).all()
            return [query.to_dict() for query in queries]
        except Exception as e:
            logger.error(f"Failed to get all queries: {str(e)}", exc_info=True)
            return []

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
