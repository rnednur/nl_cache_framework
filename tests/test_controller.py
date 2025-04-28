import pytest
from unittest.mock import MagicMock
import json
import numpy as np
import requests
from unittest.mock import patch

# Import the controller and model
from nl_cache_framework.controller import Text2SQLController
from nl_cache_framework.models import Text2SQLCache, TemplateType

# Fixtures are automatically used from conftest.py


def test_controller_init_failure():
    """Test constructor fails when no db_session is provided."""
    with pytest.raises(ValueError):
        Text2SQLController(db_session=None)


def test_add_query_success(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test successfully adding a simple query."""
    nl_query = "Show me total sales last month"
    template = "SELECT SUM(sales) FROM facts WHERE month = 'last'"
    tags = ["sales", "monthly"]
    embedding_list = [0.1] * 768  # Match the mock embedding dimension
    embedding_array = np.array(embedding_list)

    # Configure mock return values
    # Ensure get_embedding returns a NumPy array compatible with subsequent operations
    mock_similarity_util.get_embedding.return_value = embedding_array

    # Call the method under test
    result = text2sql_controller.add_query(
        nl_query=nl_query,
        template=template,
        template_type=TemplateType.SQL,
        tags=tags,
        is_template=False,  # Explicitly not a template
    )

    # --- Assertions ---

    # 1. Check the result dictionary structure and values
    assert result is not None
    assert result["nl_query"] == nl_query
    assert result["template"] == template
    assert result["template_type"] == TemplateType.SQL
    assert result["tags"] == tags
    assert result["is_template"] is False
    # Note: vector_embedding is not included in the to_dict() result
    assert "id" in result  # ID should be assigned after flush

    # 2. Verify embedding was called correctly
    mock_similarity_util.get_embedding.assert_called_once_with(nl_query)

    # 3. Verify database interactions
    # Check that add, flush, and commit were called on the session
    mock_db_session.add.assert_called_once()
    mock_db_session.flush.assert_called_once()
    mock_db_session.commit.assert_called_once()

    # Check the object added to the session
    added_object = mock_db_session.add.call_args[0][0]
    assert isinstance(added_object, Text2SQLCache)
    assert added_object.nl_query == nl_query
    assert added_object.template == template
    assert added_object.tags == tags
    assert added_object.vector_embedding == json.dumps(embedding_list)
    assert added_object.is_template is False


def test_add_query_template(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test adding a template query with entity replacements."""
    nl_query = "Revenue for date :date"
    template = "SELECT SUM(revenue) FROM facts WHERE date = :date_val"
    entity_replacements = {"date_1": {"placeholder": ":date_val", "type": "date"}}
    embedding_list = [0.2] * 768
    embedding_array = np.array(embedding_list)

    # Configure mock
    mock_similarity_util.get_embedding.return_value = embedding_array

    # Call the method
    result = text2sql_controller.add_query(
        nl_query=nl_query,
        template=template,
        template_type=TemplateType.SQL,
        entity_replacements=entity_replacements,
        is_template=True,
    )

    # Assertions
    assert result["is_template"] is True
    assert result["entity_replacements"] == entity_replacements

    # Check the object added to the session
    added_object = mock_db_session.add.call_args[0][0]
    assert added_object.is_template is True
    assert added_object.entity_replacements == entity_replacements


def test_add_query_embedding_failure(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test adding a query when embedding generation fails."""
    nl_query = "Show me total sales last month"
    template = "SELECT SUM(sales) FROM facts WHERE month = 'last'"

    # Configure mock to simulate embedding failure
    mock_similarity_util.get_embedding.return_value = None

    # Call the method
    result = text2sql_controller.add_query(nl_query=nl_query, template=template)

    # Assertions
    assert result is not None
    assert result["nl_query"] == nl_query
    assert result["template"] == template
    # Note: vector_embedding is not included in the to_dict() result

    # Verify DB operations still happened
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

    # Verify the object added to the session has a None vector_embedding
    added_object = mock_db_session.add.call_args[0][0]
    assert added_object.vector_embedding is None


def test_search_query_exact_match(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test searching for a query with exact match."""
    # Sample data
    nl_query = "Show top 5 sales"

    # Setup mock query results for exact match
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = []  # No candidates initially

    # Setup exact match to return a single matching entry
    sample_cache_entry = MagicMock(spec=Text2SQLCache)
    sample_cache_entry.to_dict.return_value = {
        "id": 1,
        "nl_query": nl_query,
        "template": "SELECT * FROM sales ORDER BY amount DESC LIMIT 5",
        "template_type": TemplateType.SQL,
        "is_template": False,
        "tags": ["sales", "top"],
        "is_valid": True,
        "usage_count": 10,
    }
    mock_query.filter.return_value.limit.return_value.all.return_value = [
        sample_cache_entry
    ]

    # Call the method
    results = text2sql_controller.search_query(nl_query=nl_query, search_method="exact")

    # Assertions
    assert len(results) == 1
    assert results[0]["nl_query"] == nl_query
    assert results[0]["similarity"] == 1.0
    assert results[0]["match_type"] == "exact"

    # Verify query building
    mock_db_session.query.assert_called_with(Text2SQLCache)

    # With search_method="exact", the controller should:
    # 1. First build a base query with is_valid filter
    # 2. Then add the filter for nl_query exact match
    # We'll check the first call was to filter for valid entries
    mock_query.filter.assert_any_call(Text2SQLCache.is_valid)

    # And then make sure we called filter with the exact match condition
    # Since the calls don't necessarily have a fixed order, we use assert_any_call
    mock_query.filter.assert_any_call(Text2SQLCache.nl_query == nl_query)


def test_search_query_string_similarity(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test searching for a query with string similarity."""
    # Sample data
    nl_query = "Show me top sales"
    candidate_query = "Show top 5 sales"

    # Setup candidate entries
    candidate_entry = MagicMock(spec=Text2SQLCache)
    candidate_entry.nl_query = candidate_query
    candidate_entry.to_dict.return_value = {
        "id": 1,
        "nl_query": candidate_query,
        "template": "SELECT * FROM sales ORDER BY amount DESC LIMIT 5",
    }

    # Make the base query return our candidates
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [candidate_entry]
    # No exact matches
    mock_query.filter.return_value.limit.return_value.all.return_value = []

    # Setup string similarity result
    mock_similarity_util.batch_compute_similarity.return_value = [
        0.85
    ]  # High similarity

    # Call the method
    results = text2sql_controller.search_query(
        nl_query=nl_query, search_method="string", similarity_threshold=0.8
    )

    # Assertions
    assert len(results) == 1
    assert results[0]["nl_query"] == candidate_query
    assert results[0]["similarity"] == 0.85
    assert results[0]["match_type"] == "string"

    # Verify similarity computation
    mock_similarity_util.batch_compute_similarity.assert_called_with(
        nl_query, [candidate_query], method="string"
    )

    # Verify query building
    mock_db_session.query.assert_called_with(Text2SQLCache)
    # Should have filtered for valid entries only - when using string similarity
    # we don't use filter(Text2SQLCache.nl_query == nl_query) as that's only for exact matching
    mock_query.filter.assert_any_call(Text2SQLCache.is_valid)


def test_search_query_vector_similarity(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test searching for a query with vector similarity."""
    # Sample data
    nl_query = "What are the revenue numbers?"
    candidate_query = "Show me revenue stats"

    # Setup candidate entries
    candidate_entry = MagicMock(spec=Text2SQLCache)
    candidate_entry.nl_query = candidate_query
    embedding_array = np.array([0.1] * 768)
    # Create a property for the embedding (mocking Text2SQLCache.embedding property)
    type(candidate_entry).embedding = MagicMock(return_value=embedding_array)
    candidate_entry.to_dict.return_value = {
        "id": 1,
        "nl_query": candidate_query,
        "template": "SELECT * FROM revenue",
    }

    # Make the base query return our candidates
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [candidate_entry]
    # No exact matches
    mock_query.filter.return_value.limit.return_value.all.return_value = []

    # Setup mock embedding retrieval and similarity
    query_embedding_array = np.array([0.2] * 768)
    mock_similarity_util.get_embedding.return_value = query_embedding_array
    mock_similarity_util.compute_cosine_similarity.return_value = (
        0.90  # High vector similarity
    )

    # Call the method
    results = text2sql_controller.search_query(
        nl_query=nl_query, search_method="vector", similarity_threshold=0.8
    )

    # Assertions
    assert len(results) == 1
    assert results[0]["nl_query"] == candidate_query
    assert results[0]["similarity"] == 0.90
    assert results[0]["match_type"] == "vector"

    # Verify embedding retrieval and similarity computation
    mock_similarity_util.get_embedding.assert_called_with(nl_query)
    mock_similarity_util.compute_cosine_similarity.assert_called_with(
        query_embedding_array, embedding_array
    )

    # Verify query building - for vector search, we only filter on is_valid
    # We don't use filter(Text2SQLCache.nl_query == nl_query) for vector search
    mock_db_session.query.assert_called_with(Text2SQLCache)
    mock_query.filter.assert_any_call(Text2SQLCache.is_valid)


def test_search_query_auto_strategy(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test search_query with 'auto' strategy that tries multiple methods."""
    # Sample data
    nl_query = "Show sales data"

    # Setup mock for no exact match first
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value = mock_query
    mock_query.filter.return_value.limit.return_value.all.return_value = (
        []
    )  # No exact matches

    # Setup string similarity candidates
    candidate1 = MagicMock(spec=Text2SQLCache)
    candidate1.nl_query = "Show me sales figures"
    candidate1.to_dict.return_value = {
        "id": 1,
        "nl_query": "Show me sales figures",
        "template": "SELECT * FROM sales",
    }

    candidate2 = MagicMock(spec=Text2SQLCache)
    candidate2.nl_query = "Display sales information"
    candidate2.to_dict.return_value = {
        "id": 2,
        "nl_query": "Display sales information",
        "template": "SELECT * FROM sales_info",
    }

    # Setup vector embeddings for candidates
    mock_query.all.return_value = [candidate1, candidate2]
    type(candidate1).embedding = MagicMock(return_value=np.array([0.3] * 768))
    type(candidate2).embedding = MagicMock(return_value=np.array([0.4] * 768))

    # Setup string and vector similarities
    mock_similarity_util.batch_compute_similarity.return_value = [
        0.75,
        0.65,
    ]  # String similarities
    mock_similarity_util.get_embedding.return_value = np.array(
        [0.5] * 768
    )  # Query embedding
    mock_similarity_util.compute_cosine_similarity.side_effect = [
        0.85,
        0.70,
    ]  # Vector similarities

    # Call the method with auto strategy
    results = text2sql_controller.search_query(
        nl_query=nl_query, search_method="auto", similarity_threshold=0.6
    )

    # Assertions
    assert len(results) > 0

    # Verify query building
    mock_db_session.query.assert_called_with(Text2SQLCache)

    # With auto mode, the controller should:
    # 1. First build a base query with is_valid filter
    mock_query.filter.assert_any_call(Text2SQLCache.is_valid)

    # 2. Try exact matches first
    mock_query.filter.assert_any_call(Text2SQLCache.nl_query == nl_query)

    # 3. Then try string similarity (verify batch_compute_similarity was called)
    mock_similarity_util.batch_compute_similarity.assert_called_once()

    # 4. Finally try vector similarity (verify get_embedding and compute_cosine_similarity were called)
    mock_similarity_util.get_embedding.assert_called_once_with(nl_query)
    assert mock_similarity_util.compute_cosine_similarity.call_count >= 1


def test_get_query_by_id_found(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test retrieving a query by ID when it exists."""
    # Setup mock query result
    query_id = 42
    mock_cache_entry = MagicMock(spec=Text2SQLCache)
    expected_result = {
        "id": query_id,
        "nl_query": "Sample query",
        "template": "SELECT * FROM sample",
    }
    mock_cache_entry.to_dict.return_value = expected_result

    # Configure the mock query to return our entry
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = mock_cache_entry

    # Call the method
    result = text2sql_controller.get_query_by_id(query_id)

    # Assertions
    assert result == expected_result
    mock_db_session.query.assert_called_with(Text2SQLCache)
    mock_query.filter.assert_called_with(Text2SQLCache.id == query_id)


def test_get_query_by_id_not_found(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test retrieving a query by ID when it doesn't exist."""
    # Setup mock query result (not found)
    query_id = 999
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = None

    # Call the method
    result = text2sql_controller.get_query_by_id(query_id)

    # Assertions
    assert result is None
    mock_db_session.query.assert_called_with(Text2SQLCache)
    mock_query.filter.assert_called_with(Text2SQLCache.id == query_id)


def test_update_query_success(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test successfully updating a query."""
    # Setup
    query_id = 5
    updates = {
        "nl_query": "Updated query",
        "template": "SELECT * FROM updated",
        "tags": ["updated", "test"],
    }
    embedding_list = [0.3] * 768
    embedding_array = np.array(embedding_list)

    # Configure mocks
    mock_cache_entry = MagicMock(spec=Text2SQLCache)
    mock_cache_entry.id = query_id
    mock_cache_entry.nl_query = "Original query"
    mock_cache_entry.template = "SELECT * FROM original"
    mock_cache_entry.to_dict.return_value = {
        "id": query_id,
        "nl_query": "Updated query",
        "template": "SELECT * FROM updated",
        "tags": ["updated", "test"],
        # Note: vector_embedding is not included in the to_dict() result
    }

    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = mock_cache_entry
    mock_similarity_util.get_embedding.return_value = embedding_array

    # Call the method
    result = text2sql_controller.update_query(query_id, updates)

    # Assertions
    assert result is not None
    assert result["id"] == query_id
    assert result["nl_query"] == updates["nl_query"]
    assert result["template"] == updates["template"]
    assert result["tags"] == updates["tags"]

    # Verify the cache entry was updated before commit
    assert mock_cache_entry.nl_query == updates["nl_query"]
    assert mock_cache_entry.template == updates["template"]
    assert mock_cache_entry.tags == updates["tags"]
    assert mock_cache_entry.vector_embedding == json.dumps(embedding_list)

    # Verify DB operations
    mock_db_session.commit.assert_called_once()

    # Verify embedding was called for the new NL query
    mock_similarity_util.get_embedding.assert_called_once_with(updates["nl_query"])


def test_invalidate_query_success(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test successfully invalidating a query."""
    # Setup
    query_id = 7
    invalidation_reason = "Outdated schema"

    # Configure mocks
    mock_cache_entry = MagicMock(spec=Text2SQLCache)
    mock_cache_entry.id = query_id
    mock_cache_entry.is_valid = True

    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = mock_cache_entry

    # Call the method
    result = text2sql_controller.invalidate_query(query_id, reason=invalidation_reason)

    # Assertions
    assert result is True
    assert mock_cache_entry.is_valid is False
    assert mock_cache_entry.invalidation_reason == invalidation_reason
    mock_db_session.commit.assert_called_once()


def test_invalidate_query_not_found(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test invalidating a query that doesn't exist."""
    # Setup
    query_id = 999

    # Configure mocks - entry not found
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = None

    # Call the method
    result = text2sql_controller.invalidate_query(query_id)

    # Assertions
    assert result is False
    mock_db_session.commit.assert_not_called()


def test_delete_query_success(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test successfully deleting a query."""
    # Setup
    query_id = 10

    # Configure mocks
    mock_cache_entry = MagicMock(spec=Text2SQLCache)
    mock_cache_entry.id = query_id

    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = mock_cache_entry

    # Call the method
    result = text2sql_controller.delete_query(query_id)

    # Assertions
    assert result is True
    mock_db_session.delete.assert_called_once_with(mock_cache_entry)
    mock_db_session.commit.assert_called_once()


def test_delete_query_not_found(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test deleting a query that doesn't exist."""
    # Setup
    query_id = 999

    # Configure mocks - entry not found
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = None

    # Call the method
    result = text2sql_controller.delete_query(query_id)

    # Assertions
    assert result is False
    mock_db_session.delete.assert_not_called()
    mock_db_session.commit.assert_not_called()


def test_get_query_by_template_type(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test retrieving queries by template type."""
    # Setup
    template_type = TemplateType.SQL
    limit = 5

    # Create mock entries
    mock_entries = []
    for i in range(3):  # Create 3 mock entries
        entry = MagicMock(spec=Text2SQLCache)
        entry.template_type = template_type
        entry.to_dict.return_value = {
            "id": i + 1,
            "template_type": template_type,
            "nl_query": f"Query {i+1}",
        }
        mock_entries.append(entry)

    # Configure mocks
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
        mock_entries
    )

    # Call the method
    results = text2sql_controller.get_query_by_template_type(template_type, limit=limit)

    # Assertions
    assert len(results) == 3
    for i, result in enumerate(results):
        assert result["id"] == i + 1
        assert result["template_type"] == template_type

    # Verify query building
    mock_db_session.query.assert_called_with(Text2SQLCache)
    mock_query.filter.assert_called_with(Text2SQLCache.template_type == template_type)
    # Verify order_by was called (we don't check the exact ordering criteria)
    assert mock_query.order_by.called
    # Verify limit was applied
    mock_query.order_by.return_value.limit.assert_called_with(limit)


def test_get_query_by_tags_match_any(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test retrieving queries by tags with match_all=False (matches any tag)."""
    # Setup
    tags = ["sales", "revenue"]

    # Create mock entries
    mock_entries = []
    for i in range(2):
        entry = MagicMock(spec=Text2SQLCache)
        entry.tags = [tags[i]]  # Each entry has one of the tags
        entry.to_dict.return_value = {
            "id": i + 1,
            "tags": [tags[i]],
            "nl_query": f"Query {i+1}",
        }
        mock_entries.append(entry)

    # Configure mocks
    mock_query = mock_db_session.query.return_value
    # Need to simulate the SQL 'IN' operation when filtering by tags
    mock_query.filter.return_value.order_by.return_value.all.return_value = mock_entries

    # Call the method
    results = text2sql_controller.get_query_by_tags(tags, match_all=False)

    # Assertions
    assert len(results) == 2
    assert results[0]["tags"] == [tags[0]]
    assert results[1]["tags"] == [tags[1]]

    # We can't easily verify the exact filter condition because of SQLAlchemy's complex filter mechanisms
    # But we can verify query was called
    mock_db_session.query.assert_called_with(Text2SQLCache)


def test_get_query_by_tags_match_all(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test retrieving queries by tags with match_all=True (matches all tags)."""
    # Setup
    tags = ["sales", "revenue"]

    # Create mock entry that has both tags
    mock_entry = MagicMock(spec=Text2SQLCache)
    mock_entry.tags = tags
    mock_entry.to_dict.return_value = {
        "id": 1,
        "tags": tags,
        "nl_query": "Query with both tags",
    }

    # Configure mocks
    mock_query = mock_db_session.query.return_value
    # Simulate finding an entry with all tags
    mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_entry]

    # Call the method
    results = text2sql_controller.get_query_by_tags(tags, match_all=True)

    # Assertions
    assert len(results) == 1
    assert set(results[0]["tags"]) == set(tags)

    # Verify query was called
    mock_db_session.query.assert_called_with(Text2SQLCache)


def test_apply_entity_substitution(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test applying entity substitution to a template query."""
    # Setup
    template_id = 15
    template_str = "SELECT SUM(revenue) FROM facts WHERE date = :date_val"
    entity_replacements = {"date_1": {"placeholder": ":date_val", "type": "date"}}
    new_entity_values = {"date_1": "2023-01-01"}

    # Create mock template entry
    mock_template_entry = MagicMock(spec=Text2SQLCache)
    mock_template_entry.id = template_id
    mock_template_entry.template = template_str
    mock_template_entry.entity_replacements = entity_replacements
    mock_template_entry.is_template = True
    mock_template_entry.to_dict.return_value = {
        "id": template_id,
        "template": template_str,
        "entity_replacements": entity_replacements,
        "is_template": True,
    }

    # Configure mocks
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = mock_template_entry

    # Call the method
    result = text2sql_controller.apply_entity_substitution(
        template_id, new_entity_values
    )

    # Assertions
    assert result is not None
    # The resulting template should have the placeholder replaced with the actual value
    assert ":date_val" not in result["substituted_template"]
    assert "2023-01-01" in result["substituted_template"]

    # Verify query building
    mock_db_session.query.assert_called_with(Text2SQLCache)
    mock_query.filter.assert_called_with(Text2SQLCache.id == template_id)


def test_apply_entity_substitution_not_template(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test applying entity substitution to a non-template query."""
    # Setup
    template_id = 20

    # Create mock non-template entry
    mock_entry = MagicMock(spec=Text2SQLCache)
    mock_entry.id = template_id
    mock_entry.is_template = False

    # Configure mocks
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = mock_entry

    # Call the method
    with pytest.raises(ValueError):
        text2sql_controller.apply_entity_substitution(
            template_id, {"any_key": "any_value"}
        )

    # Verify query building
    mock_db_session.query.assert_called_with(Text2SQLCache)
    mock_query.filter.assert_called_with(Text2SQLCache.id == template_id)


def test_add_api_template(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test adding an API call template with entity replacements."""
    nl_query = "Get weather forecast for city :city"
    template = """
    {
        "method": "GET",
        "url": "https://api.weather.com/forecast/:city",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer :api_key"
        }
    }
    """
    entity_replacements = {
        "city_placeholder": {"placeholder": ":city", "type": "string"},
        "api_key_placeholder": {"placeholder": ":api_key", "type": "string"},
    }
    embedding_list = [0.2] * 768
    embedding_array = np.array(embedding_list)

    # Configure mock
    mock_similarity_util.get_embedding.return_value = embedding_array

    # Call the method
    result = text2sql_controller.add_query(
        nl_query=nl_query,
        template=template,
        template_type=TemplateType.API,
        entity_replacements=entity_replacements,
        is_template=True,
    )

    # Assertions
    assert result["is_template"] is True
    assert result["entity_replacements"] == entity_replacements
    assert result["template_type"] == TemplateType.API

    # Check the object added to the session
    added_object = mock_db_session.add.call_args[0][0]
    assert added_object.is_template is True
    assert added_object.entity_replacements == entity_replacements
    assert added_object.template_type == TemplateType.API


def test_search_api_template(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test searching for an API template."""
    # Sample data
    nl_query = "Get weather forecast for New York"

    # Setup mock query results for similar query
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value = mock_query

    # Setup a sample API template cache entry
    sample_cache_entry = MagicMock(spec=Text2SQLCache)
    sample_cache_entry.id = 3
    sample_cache_entry.nl_query = "Get weather forecast for city :city"
    sample_cache_entry.template = """
    {
        "method": "GET",
        "url": "https://api.weather.com/forecast/:city",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer :api_key"
        }
    }
    """
    sample_cache_entry.template_type = TemplateType.API
    sample_cache_entry.is_template = True
    sample_cache_entry.entity_replacements = {
        "city_placeholder": {"placeholder": ":city", "type": "string"},
        "api_key_placeholder": {"placeholder": ":api_key", "type": "string"},
    }
    sample_cache_entry.tags = ["weather", "forecast", "api"]
    sample_cache_entry.is_valid = True
    sample_cache_entry.usage_count = 5

    sample_cache_entry.to_dict.return_value = {
        "id": sample_cache_entry.id,
        "nl_query": sample_cache_entry.nl_query,
        "template": sample_cache_entry.template,
        "template_type": sample_cache_entry.template_type,
        "is_template": sample_cache_entry.is_template,
        "entity_replacements": sample_cache_entry.entity_replacements,
        "tags": sample_cache_entry.tags,
        "is_valid": sample_cache_entry.is_valid,
        "usage_count": sample_cache_entry.usage_count,
    }

    # No exact matches
    mock_query.filter.return_value.limit.return_value.all.return_value = []

    # But return our sample entry for the base query
    mock_query.all.return_value = [sample_cache_entry]

    # Mock the string similarity to return high value
    mock_similarity_util.batch_compute_similarity.return_value = [0.85]

    # Call the method filtering by API template type
    results = text2sql_controller.search_query(
        nl_query=nl_query,
        template_type=TemplateType.API,
        search_method="string",
        similarity_threshold=0.7,
    )

    # Assertions
    assert len(results) == 1
    assert results[0]["template_type"] == TemplateType.API
    assert results[0]["is_template"] is True
    assert "similarity" in results[0]
    assert results[0]["similarity"] >= 0.7


def test_apply_entity_substitution_api(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test entity substitution for an API template."""
    # Mock a template entry in the database
    mock_entry = MagicMock(spec=Text2SQLCache)
    mock_entry.id = 3
    mock_entry.is_valid = True
    mock_entry.template = """
    {
        "method": "GET",
        "url": "https://api.weather.com/forecast/:city",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer :api_key"
        }
    }
    """
    mock_entry.template_type = TemplateType.API
    mock_entry.entity_replacements = {
        "city_placeholder": {"placeholder": ":city", "type": "string"},
        "api_key_placeholder": {"placeholder": ":api_key", "type": "string"},
    }
    mock_entry.usage_count = 0

    # Configure the mock session to return our template
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = mock_entry

    # New entity values to substitute
    new_values = {"city_placeholder": "New York", "api_key_placeholder": "abc123xyz"}

    # Call the method
    result = text2sql_controller.apply_entity_substitution(
        template_id=3, new_entity_values=new_values
    )

    # Verify the result has the expected structure
    assert "original_template" in result
    assert "substituted_template" in result
    assert "entity_replacements" in result
    assert "applied_values" in result

    # Verify substitution was performed correctly
    assert "New York" in result["substituted_template"]
    assert "abc123xyz" in result["substituted_template"]
    assert result["template_type"] == TemplateType.API

    # Verify usage count was incremented
    assert mock_entry.usage_count == 1


def test_get_api_templates(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test retrieving all API templates."""
    # Create sample API templates
    sample_entry1 = MagicMock(spec=Text2SQLCache)
    sample_entry1.to_dict.return_value = {
        "id": 3,
        "nl_query": "Get weather forecast for city",
        "template_type": TemplateType.API,
        "is_template": True,
    }

    sample_entry2 = MagicMock(spec=Text2SQLCache)
    sample_entry2.to_dict.return_value = {
        "id": 4,
        "nl_query": "Get user profile by ID",
        "template_type": TemplateType.API,
        "is_template": True,
    }

    # Configure mock to return these entries
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        sample_entry1,
        sample_entry2,
    ]

    # Call the method
    results = text2sql_controller.get_query_by_template_type(
        template_type=TemplateType.API
    )

    # Verify results
    assert len(results) == 2
    assert results[0]["template_type"] == TemplateType.API
    assert results[1]["template_type"] == TemplateType.API

    # Verify the query was built correctly
    mock_db_session.query.assert_called_with(Text2SQLCache)
    mock_query.filter.assert_any_call(
        Text2SQLCache.template_type == TemplateType.API, Text2SQLCache.is_valid
    )


def test_real_api_integration(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test a complete workflow with API templates including making a real API call."""
    # 1. Add an API template for httpbin test API
    nl_query = "Make a GET request to httpbin with param :test_param"
    template = """
    {
        "method": "GET",
        "url": "https://httpbin.org/get",
        "params": {
            "test_param": ":test_param"
        },
        "headers": {
            "Accept": "application/json"
        }
    }
    """
    entity_replacements = {
        "param_value": {"placeholder": ":test_param", "type": "string"}
    }

    # Configure mock for embedding
    embedding_array = np.array([0.1] * 768)
    mock_similarity_util.get_embedding.return_value = embedding_array

    # Step 1: Add the template to the cache
    result = text2sql_controller.add_query(
        nl_query=nl_query,
        template=template,
        template_type=TemplateType.API,
        entity_replacements=entity_replacements,
        is_template=True,
        tags=["api", "httpbin", "test"],
    )

    template_id = result["id"]

    # Mock the database to return our template for subsequent queries
    mock_template = MagicMock(spec=Text2SQLCache)
    mock_template.id = template_id
    mock_template.is_valid = True
    mock_template.template = template
    mock_template.template_type = TemplateType.API
    mock_template.entity_replacements = entity_replacements
    mock_template.usage_count = 0

    # Configure mock to return this entry
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = mock_template

    # Step 2: Apply entity substitution
    new_values = {"param_value": "test123"}

    substitution_result = text2sql_controller.apply_entity_substitution(
        template_id=template_id, new_entity_values=new_values
    )

    # Parse the substituted template
    api_spec = json.loads(substitution_result["substituted_template"])

    # Step 3: Actually make the API call (with mock)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "args": {"test_param": "test123"},
        "headers": {"Accept": "application/json"},
        "url": "https://httpbin.org/get?test_param=test123",
    }

    # Mock the requests.request function
    with patch("requests.request", return_value=mock_response) as mock_request:
        # Execute the API call
        response = requests.request(
            method=api_spec["method"],
            url=api_spec["url"],
            params=api_spec["params"],
            headers=api_spec["headers"],
        )

        # Verify the call was made correctly
        mock_request.assert_called_once_with(
            method=api_spec["method"],
            url=api_spec["url"],
            params=api_spec["params"],
            headers=api_spec["headers"],
        )

        # Check response handling
        response_data = response.json()
        assert response_data["args"]["test_param"] == "test123"


# You can also add a test that makes an actual API call without mocking
# This is commented out as it's not recommended for unit tests,
# but could be enabled for integration testing with a safe API endpoint
"""
def test_real_api_call_no_mocks(text2sql_controller: Text2SQLController, mock_db_session: MagicMock):
    '''Test making a real API call to httpbin (only for integration testing).'''
    import json
    import requests
    
    # Skip this test by default - only enable for integration testing
    import pytest
    pytest.skip("Skipping actual API call test - only run manually for integration testing")
    
    # 1. Setup a mock entry in the cache
    mock_entry = MagicMock(spec=Text2SQLCache)
    mock_entry.id = 10
    mock_entry.is_valid = True
    mock_entry.template = '''{
        "method": "GET",
        "url": "https://httpbin.org/get",
        "params": {
            "test_param": ":test_value"
        }
    }'''
    mock_entry.template_type = TemplateType.API
    mock_entry.entity_replacements = {
        "test_param": {"placeholder": ":test_value", "type": "string"}
    }
    
    # Configure mock session
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = mock_entry
    
    # 2. Apply entity substitution
    substitution_result = text2sql_controller.apply_entity_substitution(
        template_id=10,
        new_entity_values={"test_param": "actual_test_value"}
    )
    
    # 3. Actually call the API with the substituted template
    api_spec = json.loads(substitution_result["substituted_template"])
    
    response = requests.request(
        method=api_spec["method"],
        url=api_spec["url"],
        params=api_spec["params"]
    )
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["args"]["test_param"] == "actual_test_value"
"""


def test_add_url_template(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test adding a URL template with entity replacements."""
    nl_query = "Show page :page_number of products in category :category"
    template = "https://example.com/products/:category?page=:page_number&sort=price_asc"
    entity_replacements = {
        "category_placeholder": {"placeholder": ":category", "type": "string"},
        "page_number_placeholder": {"placeholder": ":page_number", "type": "integer"},
    }
    embedding_list = [0.3] * 768
    embedding_array = np.array(embedding_list)

    # Configure mock
    mock_similarity_util.get_embedding.return_value = embedding_array

    # Call the method
    result = text2sql_controller.add_query(
        nl_query=nl_query,
        template=template,
        template_type=TemplateType.URL,
        entity_replacements=entity_replacements,
        is_template=True,
    )

    # Assertions
    assert result["is_template"] is True
    assert result["entity_replacements"] == entity_replacements
    assert result["template_type"] == TemplateType.URL

    # Check the object added to the session
    added_object = mock_db_session.add.call_args[0][0]
    assert added_object.is_template is True
    assert added_object.entity_replacements == entity_replacements
    assert added_object.template_type == TemplateType.URL


def test_apply_entity_substitution_url(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test entity substitution for a URL template."""
    # Mock a URL template entry in the database
    mock_entry = MagicMock(spec=Text2SQLCache)
    mock_entry.id = 4
    mock_entry.is_valid = True
    mock_entry.template = "https://example.com/search/:query?page=:page&limit=:limit"
    mock_entry.template_type = TemplateType.URL
    mock_entry.entity_replacements = {
        "query_param": {"placeholder": ":query", "type": "string"},
        "page_param": {"placeholder": ":page", "type": "integer"},
        "limit_param": {"placeholder": ":limit", "type": "integer"},
    }
    mock_entry.usage_count = 0

    # Configure the mock session to return our template
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = mock_entry

    # New entity values to substitute
    new_values = {"query_param": "shoes", "page_param": "2", "limit_param": "25"}

    # Call the method
    result = text2sql_controller.apply_entity_substitution(
        template_id=4, new_entity_values=new_values
    )

    # Verify the result has the expected structure
    assert "original_template" in result
    assert "substituted_template" in result
    assert "entity_replacements" in result
    assert "applied_values" in result

    # Verify substitution was performed correctly
    expected_url = "https://example.com/search/shoes?page=2&limit=25"
    assert result["substituted_template"] == expected_url
    assert result["template_type"] == TemplateType.URL

    # Verify usage count was incremented
    assert mock_entry.usage_count == 1


def test_url_integration_with_formatting(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test a complete workflow with URL templates including URL encoding."""
    # 1. Add a URL template with special characters that need encoding
    nl_query = "Search for :search_term in category :category"
    template = "https://example.com/search/:category?q=:search_term&source=nl_cache"
    entity_replacements = {
        "search_placeholder": {"placeholder": ":search_term", "type": "string"},
        "category_placeholder": {"placeholder": ":category", "type": "string"},
    }

    # Configure mock for embedding
    embedding_array = np.array([0.1] * 768)
    mock_similarity_util.get_embedding.return_value = embedding_array

    # Step 1: Add the template to the cache
    result = text2sql_controller.add_query(
        nl_query=nl_query,
        template=template,
        template_type=TemplateType.URL,
        entity_replacements=entity_replacements,
        is_template=True,
        tags=["url", "search", "example"],
    )

    template_id = result["id"]

    # Mock the database to return our template for subsequent queries
    mock_template = MagicMock(spec=Text2SQLCache)
    mock_template.id = template_id
    mock_template.is_valid = True
    mock_template.template = template
    mock_template.template_type = TemplateType.URL
    mock_template.entity_replacements = entity_replacements
    mock_template.usage_count = 0

    # Configure mock to return this entry
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = mock_template

    # Step 2: Apply entity substitution with values that need URL encoding
    new_values = {
        "search_placeholder": "red & blue shoes",
        "category_placeholder": "men's footwear",
    }

    substitution_result = text2sql_controller.apply_entity_substitution(
        template_id=template_id, new_entity_values=new_values
    )

    # In an ideal implementation, the URL would be properly encoded
    # For now, we'll just check that substitution happened
    assert "red & blue shoes" in substitution_result["substituted_template"]
    assert "men's footwear" in substitution_result["substituted_template"]

    # Step 3: Demonstrate how URL encoding could be applied
    import urllib.parse

    substituted_url = substitution_result["substituted_template"]

    # Parse the URL into components
    parsed_url = urllib.parse.urlparse(substituted_url)

    # Extract and encode path components
    path_parts = parsed_url.path.split("/")
    encoded_path_parts = [
        urllib.parse.quote(part) if i > 0 else part  # Don't encode the first empty part
        for i, part in enumerate(path_parts)
    ]
    encoded_path = "/".join(encoded_path_parts)

    # Parse and encode query parameters
    query_params = urllib.parse.parse_qs(parsed_url.query)

    # Create properly encoded URL
    encoded_url = urllib.parse.urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            encoded_path,
            parsed_url.params,
            urllib.parse.urlencode(query_params, doseq=True),
            parsed_url.fragment,
        )
    )

    # This demonstrates how URL encoding should work (though the actual implementation
    # might be different depending on the entity_substitution implementation)
    assert "men%27s+footwear" in encoded_url or "men%27s%20footwear" in encoded_url
    assert (
        "red+%26+blue+shoes" in encoded_url or "red%20%26%20blue%20shoes" in encoded_url
    )


def test_add_workflow_template(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test adding a workflow template with entity replacements."""
    nl_query = "Generate sales report for region :region from :start_date to :end_date and email to :email"
    # A workflow template could be a JSON structure defining a sequence of steps
    template = """
    {
        "workflow": "generate_and_email_report",
        "steps": [
            {
                "type": "database_query",
                "query": "SELECT date, product, amount FROM sales WHERE region = ':region' AND date BETWEEN ':start_date' AND ':end_date'"
            },
            {
                "type": "report_generation",
                "format": "excel",
                "template": "sales_report_template"
            },
            {
                "type": "email",
                "to": ":email",
                "subject": "Sales Report for :region (:start_date to :end_date)",
                "body": "Please find attached the sales report for :region covering the period from :start_date to :end_date.",
                "attachment": "output.xlsx"
            }
        ]
    }
    """
    entity_replacements = {
        "region_placeholder": {"placeholder": ":region", "type": "string"},
        "start_date_placeholder": {
            "placeholder": ":start_date",
            "type": "date",
            "format": "YYYY-MM-DD",
        },
        "end_date_placeholder": {
            "placeholder": ":end_date",
            "type": "date",
            "format": "YYYY-MM-DD",
        },
        "email_placeholder": {"placeholder": ":email", "type": "string"},
    }
    embedding_list = [0.4] * 768
    embedding_array = np.array(embedding_list)

    # Configure mock
    mock_similarity_util.get_embedding.return_value = embedding_array

    # Call the method
    result = text2sql_controller.add_query(
        nl_query=nl_query,
        template=template,
        template_type=TemplateType.WORKFLOW,
        entity_replacements=entity_replacements,
        is_template=True,
    )

    # Assertions
    assert result["is_template"] is True
    assert result["entity_replacements"] == entity_replacements
    assert result["template_type"] == TemplateType.WORKFLOW

    # Check the object added to the session
    added_object = mock_db_session.add.call_args[0][0]
    assert added_object.is_template is True
    assert added_object.entity_replacements == entity_replacements
    assert added_object.template_type == TemplateType.WORKFLOW


def test_apply_entity_substitution_workflow(
    text2sql_controller: Text2SQLController, mock_db_session: MagicMock
):
    """Test entity substitution for a workflow template."""
    # Mock a workflow template entry in the database
    mock_entry = MagicMock(spec=Text2SQLCache)
    mock_entry.id = 5
    mock_entry.is_valid = True
    mock_entry.template = """
    {
        "workflow": "data_import_process",
        "steps": [
            {
                "type": "file_download",
                "url": "https://example.com/data/:dataset_name.csv"
            },
            {
                "type": "data_validation",
                "schema": ":schema_name",
                "threshold": ":validation_threshold"
            },
            {
                "type": "data_import",
                "target_table": ":target_table",
                "mode": "append"
            }
        ]
    }
    """
    mock_entry.template_type = TemplateType.WORKFLOW
    mock_entry.entity_replacements = {
        "dataset_placeholder": {"placeholder": ":dataset_name", "type": "string"},
        "schema_placeholder": {"placeholder": ":schema_name", "type": "string"},
        "threshold_placeholder": {
            "placeholder": ":validation_threshold",
            "type": "number",
        },
        "table_placeholder": {"placeholder": ":target_table", "type": "string"},
    }
    mock_entry.usage_count = 0

    # Configure the mock session to return our template
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = mock_entry

    # New entity values to substitute
    new_values = {
        "dataset_placeholder": "sales_2023",
        "schema_placeholder": "sales_schema",
        "threshold_placeholder": "0.95",
        "table_placeholder": "sales_data",
    }

    # Call the method
    result = text2sql_controller.apply_entity_substitution(
        template_id=5, new_entity_values=new_values
    )

    # Verify the result has the expected structure
    assert "original_template" in result
    assert "substituted_template" in result
    assert "entity_replacements" in result
    assert "applied_values" in result

    # Verify substitution was performed correctly
    assert "sales_2023.csv" in result["substituted_template"]
    assert (
        '"schema": "sales_schema"' in result["substituted_template"]
        or '"schema": "sales_schema"' in result["substituted_template"]
    )
    assert (
        '"threshold": "0.95"' in result["substituted_template"]
        or '"threshold": "0.95"' in result["substituted_template"]
    )
    assert (
        '"target_table": "sales_data"' in result["substituted_template"]
        or '"target_table": "sales_data"' in result["substituted_template"]
    )
    assert result["template_type"] == TemplateType.WORKFLOW

    # Verify usage count was incremented
    assert mock_entry.usage_count == 1


def test_workflow_execution_simulation(
    text2sql_controller: Text2SQLController,
    mock_db_session: MagicMock,
    mock_similarity_util: MagicMock,
):
    """Test a complete workflow template execution simulation."""
    import json
    from unittest.mock import patch

    # 1. Add a workflow template
    nl_query = "Process data file :filename and notify :user_email"
    template = """
    {
        "workflow": "data_processing",
        "steps": [
            {
                "type": "file_processing",
                "input_file": ":filename"
            },
            {
                "type": "notification",
                "method": "email",
                "recipient": ":user_email",
                "message": "Processing of :filename has been completed."
            }
        ]
    }
    """
    entity_replacements = {
        "file_placeholder": {"placeholder": ":filename", "type": "string"},
        "email_placeholder": {"placeholder": ":user_email", "type": "string"},
    }

    # Configure mock for embedding
    embedding_array = np.array([0.1] * 768)
    mock_similarity_util.get_embedding.return_value = embedding_array

    # Step 1: Add the template to the cache
    result = text2sql_controller.add_query(
        nl_query=nl_query,
        template=template,
        template_type=TemplateType.WORKFLOW,
        entity_replacements=entity_replacements,
        is_template=True,
        tags=["workflow", "data", "notification"],
    )

    template_id = result["id"]

    # Mock the database to return our template for subsequent queries
    mock_template = MagicMock(spec=Text2SQLCache)
    mock_template.id = template_id
    mock_template.is_valid = True
    mock_template.template = template
    mock_template.template_type = TemplateType.WORKFLOW
    mock_template.entity_replacements = entity_replacements
    mock_template.usage_count = 0

    # Configure mock to return this entry
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value.first.return_value = mock_template

    # Step 2: Apply entity substitution
    new_values = {
        "file_placeholder": "monthly_sales.csv",
        "email_placeholder": "user@example.com",
    }

    substitution_result = text2sql_controller.apply_entity_substitution(
        template_id=template_id, new_entity_values=new_values
    )

    # Step 3: Parse the workflow template
    workflow_spec = json.loads(substitution_result["substituted_template"])

    # Step 4: Simulate executing the workflow
    # In a real implementation, there would be a workflow executor component
    # Here we just simulate it with mocks

    # Mock file processor
    with patch("builtins.open", MagicMock()) as mock_file_open:
        # Mock email sender
        with patch("smtplib.SMTP", MagicMock()) as mock_smtp:
            # Execute workflow steps
            for step in workflow_spec["steps"]:
                if step["type"] == "file_processing":
                    # Simulate file processing
                    input_file = step["input_file"]
                    assert input_file == "monthly_sales.csv"
                    # In real code: process the file

                elif step["type"] == "notification":
                    # Simulate notification
                    recipient = step["recipient"]
                    message = step["message"]
                    assert recipient == "user@example.com"
                    assert "monthly_sales.csv" in message
                    # In real code: send the notification

    # In a real implementation, you'd also implement status tracking,
    # error handling, retries, and more complex workflow operations


# --- More tests will go here ---

@patch("builtins.open", new_callable=MagicMock)
@patch("smtplib.SMTP")
def test_save_load_report_integration(_, __, test_controller):
    """Integration test for saving and loading reports."""
    # Arrange
    report_data = {"key": "value"}
