# Placeholder for test configuration

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
import numpy as np
import json

# Import from the library package
from thinkforge.controller import Text2SQLController
from thinkforge.similarity import Text2SQLSimilarity
from thinkforge.models import Text2SQLCache, TemplateType, Status

# Sample data for mocking DB returns
SAMPLE_CACHE_ENTRY_EXACT = Text2SQLCache(
    id=1,
    nl_query="Show me all customers in New York",
    template="SELECT * FROM customers WHERE city = 'New York';",
    template_type=TemplateType.SQL,
    status=Status.ACTIVE,
    vector_embedding=[0.1] * 768,  # Simplified embedding
)

SAMPLE_CACHE_ENTRY_TEMPLATE = Text2SQLCache(
    id=3,
    nl_query="Show sales for {client}",
    template="SELECT * FROM sales WHERE client = :client;",
    template_type=TemplateType.SQL,
    is_template=True,
    entity_replacements={"client": {"placeholder": ":client", "type": "string"}},
    status=Status.ACTIVE,
    vector_embedding=[0.2] * 768,
)

SAMPLE_CACHE_ENTRY_SIMILAR = Text2SQLCache(
    id=2,
    nl_query="List all clients in NY",
    template="SELECT * FROM customers WHERE state = 'NY';",
    template_type=TemplateType.SQL,
    status=Status.ACTIVE,
    vector_embedding=[0.11] * 768,  # Slightly different embedding
)

SAMPLE_CACHE_ENTRY_WORKFLOW = Text2SQLCache(
    id=4,
    nl_query="Run sales report workflow",
    template=json.dumps({
        "steps": [
            {"cache_id": 1, "type": "sequential", "description": "Fetch data"},
            {"cache_id": 2, "type": "sequential", "description": "Process data"}
        ]
    }),
    template_type=TemplateType.WORKFLOW,
    status=Status.ACTIVE,
    vector_embedding=[0.3] * 768,
)


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Provides a MagicMock simulating a SQLAlchemy Session."""
    session = MagicMock(spec=Session)
    # Configure query methods
    mock_query = MagicMock()
    session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query  # Allow chaining filter
    mock_query.filter_by.return_value = mock_query  # Allow chaining filter_by
    mock_query.order_by.return_value = mock_query  # Allow chaining order_by
    mock_query.limit.return_value = mock_query  # Allow chaining limit
    # Default return values for common query terminators
    mock_query.first.return_value = None
    mock_query.all.return_value = []
    mock_query.count.return_value = 0
    return session


@pytest.fixture
def mock_similarity_util() -> MagicMock:
    """Provides a MagicMock simulating the Text2SQLSimilarity utility."""
    mock_util = MagicMock(spec=Text2SQLSimilarity)
    # Mock get_embedding to return a dummy array of the correct shape (e.g., 768 for mpnet)
    mock_util.get_embedding.return_value = MagicMock(spec=np.ndarray)
    mock_util.get_embedding.return_value.tolist.return_value = [
        0.1
    ] * 768  # Dummy embedding list
    mock_util.get_embedding.return_value.ndim = (
        1  # Simulate 1D output for single strings
    )
    mock_util.compute_string_similarity.return_value = 0.0  # Default string sim
    mock_util.batch_compute_similarity.return_value = []  # Default batch sim
    mock_util.compute_cosine_similarity.return_value = 0.0  # Default cosine sim
    return mock_util


@pytest.fixture
def text2sql_controller(
    mock_db_session: MagicMock, mock_similarity_util: MagicMock
) -> Text2SQLController:
    """Provides a Text2SQLController instance with mocked dependencies."""
    # Patch the Text2SQLSimilarity instantiation within the controller's scope
    with patch(
        "thinkforge.controller.Text2SQLSimilarity",
        return_value=mock_similarity_util,
    ):
        controller = Text2SQLController(db_session=mock_db_session)
        # Ensure the controller is using the mocked similarity util
        controller.similarity_util = mock_similarity_util
        return controller
