import pytest
from unittest.mock import MagicMock, patch
from DataTypes import Faculty
from FacultyAgent import FacultyAgent

# --- Fixtures ---

@pytest.fixture
def mock_storage():
    """Mocks the BaseStorage interface."""
    storage = MagicMock()
    # Default to empty cache
    storage.search_cache.return_value = []
    return storage

@pytest.fixture
def agent(mock_storage):
    """Initializes FacultyAgent with mocked storage."""
    return FacultyAgent(storage=mock_storage, email="test@example.com")

# --- Test Cases ---

def test_get_experts_cache_hit(agent, mock_storage):
    """Verify agent uses cache and skips API when matches are found."""
    # 1. Setup: Create a cached faculty member
    cached_faculty = Faculty(
        name="Cached Expert",
        id="https://openalex.org/A1",
        h_index=100,
        specialty="CS",
        top_paper="Old Paper",
        last_known_institution="UCLA" # Must match school_name logic
    )
    mock_storage.search_cache.return_value = [cached_faculty]

    # 2. Execute
    with patch('requests.get') as mock_get:
        results = agent.get_experts("UCLA", "Graph Neural Networks")

        # 3. Assertions
        assert len(results) == 1
        assert results[0].name == "Cached Expert"
        mock_get.assert_not_called() # Crucial: API was never hit

@patch('requests.get')
def test_get_experts_api_flow(mock_get, agent, mock_storage):
    """Verify full API flow: Institution -> Works -> Authors -> Filter -> Cache."""
    
    # 1. Setup: Mock the three-stage API response
    school_id = "https://openalex.org/I1"
    
    mock_inst_resp = {"results": [{"id": school_id, "display_name": "UCLA"}]}
    
    mock_works_resp = {"results": [{
        "title": "GNN Paper",
        "authorships": [{
            "author": {"id": "https://openalex.org/A1"},
            "institutions": [{"id": school_id}]
        }]
    }]}
    
    mock_author_resp = {"results": [{
        "id": "https://openalex.org/A1",
        "display_name": "Dr. Graph",
        "summary_stats": {"h_index": 42},
        "last_known_institutions": [{"id": school_id}],
        "topics": [{
            "field": {"display_name": "Computer Science"},
            "display_name": "Deep Learning"
        }]
    }]}

    mock_get.side_effect = [
        MagicMock(json=lambda: mock_inst_resp),
        MagicMock(json=lambda: mock_works_resp),
        MagicMock(json=lambda: mock_author_resp)
    ]

    # 2. Execute
    results = agent.get_experts("UCLA", "Graph Neural Networks")

    # 3. Assertions
    assert len(results) == 1
    assert results[0].name == "Dr. Graph"
    assert results[0].specialty == "Deep Learning"
    
    # Verify the results were saved to storage
    mock_storage.save_faculty.assert_called_once()

@patch('requests.get')
def test_filter_out_non_cs(mock_get, agent, mock_storage):
    """Verify that researchers NOT in Computer Science are filtered out."""
    
    school_id = "https://openalex.org/I1"
    
    # Mock responses where the author is a Chemist
    mock_get.side_effect = [
        MagicMock(json=lambda: {"results": [{"id": school_id, "display_name": "UCLA"}]}),
        MagicMock(json=lambda: {"results": [{
            "title": "Molecule Paper",
            "authorships": [{"author": {"id": "A2"}, "institutions": [{"id": school_id}]}]
        }]}),
        MagicMock(json=lambda: {"results": [{
            "id": "A2",
            "display_name": "Dr. Chemistry",
            "summary_stats": {"h_index": 10},
            "last_known_institutions": [{"id": school_id}],
            "topics": [{"field": {"display_name": "Chemistry"}}] # Not Computer Science
        }]})
    ]

    results = agent.get_experts("UCLA", "Graph Neural Networks")

    # Should be empty because of the CS Field Lock
    assert len(results) == 0

def test_user_agent_no_email(mock_storage):
    """Verify User-Agent string construction when email is missing."""
    agent_no_email = FacultyAgent(storage=mock_storage, email=None)
    assert agent_no_email.headers["User-Agent"] == "FacultyAgent/1.0"