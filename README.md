# ThinkForge

A framework for caching natural language queries and their corresponding structured outputs (like SQL, API calls, etc.) to improve retrieval and performance using similarity search.

## Overview

ThinkForge is designed to cache natural language (NL) queries and map them to structured outputs such as SQL queries, API calls, URLs, or other templates. It uses embeddings for similarity search to retrieve the most relevant cached entry for a given input query, enhancing response accuracy and speed for applications dealing with natural language processing.

## Key Features

- **Semantic Similarity Search**: Uses embeddings to find the most relevant cached entries for natural language queries
- **Multiple Template Types**: Supports SQL, API calls, URLs, and workflow templates
- **Entity Extraction and Substitution**: Intelligently extracts entities from queries and applies them to templates
- **Full CRUD API**: Complete REST API for managing cache entries
- **Interactive Dashboard**: User-friendly interface for managing and testing cache entries
- **Reasoning Trace Capture**: Records the reasoning process for template generation
- **Template Validation**: Ensures templates meet quality standards
- **Usage Tracking**: Logs usage statistics for analytics purposes

## Data Model

The core data model revolves around the `Text2SQLCache` table, which stores cached entries with their embeddings for similarity search. Below is a detailed view of the data model and related classes.

```mermaid
classDiagram
    class Text2SQLCache {
        +int id
        +string nl_query
        +string template
        +string template_type
        +list vector_embedding
        +bool is_template
        +dict entity_replacements
        +string reasoning_trace
        +list tags
        +string suggested_visualization
        +string database_name
        +string schema_name
        +int catalog_id
        +bool is_valid
        +string invalidation_reason
        +datetime created_at
        +datetime updated_at
        +np.ndarray embedding()
        +dict to_dict()
        +classmethod from_dict(dict)
    }
    
    class UsageLog {
        +int id
        +int cache_entry_id
        +datetime timestamp
    }
    
    class TemplateType {
        <<enumeration>>
        SQL
        URL
        API
        WORKFLOW
    }
    
    class Text2SQLController {
        -Session session
        -Text2SQLSimilarity similarity_util
        +add_query()
        +search_query()
        +get_query_by_id()
        +update_query()
        +invalidate_query()
        +delete_query()
        +apply_entity_substitution()
    }
    
    class Text2SQLSimilarity {
        -dict _model_cache
        -SentenceTransformer model
        +get_embedding()
        +compute_string_similarity()
        +compute_cosine_similarity()
        +batch_compute_similarity()
    }
    
    class Text2SQLEntitySubstitution {
        +extract_placeholders()
        +extract_entities()
        +apply_substitution()
        +apply_sql_substitution()
        +apply_url_substitution()
        +apply_api_substitution()
    }
    
    Text2SQLCache --o TemplateType
    UsageLog --> Text2SQLCache
    Text2SQLController --> Text2SQLCache : manages
    Text2SQLController --> Text2SQLSimilarity : uses
    Text2SQLController --> Text2SQLEntitySubstitution : uses
    note for Text2SQLCache "Stores natural language queries and their structured templates with embeddings for similarity search"
```

## Framework Architecture

The framework consists of backend services for managing cache entries and similarity search, and a frontend for user interaction. Below is a detailed flowchart of the components and their interactions.

```mermaid
flowchart TD
    %% Main Flow
    Client(Client Application) -->|NL Query Request| FastAPI[FastAPI Backend]
    FastAPI -->|/v1/complete| NLQueryHandler[NL Query Handler]
    
    %% Core ThinkForge Components
    subgraph "ThinkForge"
        NLQueryHandler -->|Check Cache| Controller[Text2SQLController]
        Controller -->|Search Query| SimilarityUtil[Text2SQLSimilarity]
        Controller -->|CRUD Operations| DBModels[Database Models]
        Controller -->|Entity Handling| EntitySub[Text2SQLEntitySubstitution]
        
        %% Similarity Component
        SimilarityUtil -->|Vector Embeddings| SentenceTransformer[Sentence Transformer]
        SimilarityUtil -->|String Similarity| SequenceMatcher[Sequence Matcher]
        
        %% Entity Substitution Component
        EntitySub -->|Extract Placeholders| Templates[(Templates)]
        EntitySub -->|Extract Entities| NLQuery[(NL Queries)]
        EntitySub -->|Apply Substitution| CompletedTemplate[(Completed Templates)]
    end
    
    %% Database
    subgraph "Database"
        DBModels -->|Store/Retrieve| CacheEntries[(Text2SQLCache)]
        DBModels -->|Log Usage| UsageLog[(UsageLog)]
    end
    
    %% Response Paths
    NLQueryHandler -->|Cache Hit| CacheHitResponse[Cache Hit Response]
    NLQueryHandler -->|Cache Miss| CacheMissResponse[Cache Miss Response]
    
    CacheHitResponse --> ResponseToClient[Response to Client]
    CacheMissResponse --> ResponseToClient
    
    %% Other API Endpoints
    FastAPI -->|/v1/cache| CacheManagement[Cache Management]
    CacheManagement -->|CRUD Operations| Controller
    
    %% API Routes Legend
    classDef apiEndpoint fill:#f9f,stroke:#333,stroke-width:2px;
    class FastAPI,CacheManagement,NLQueryHandler apiEndpoint;
    
    %% Component Legend
    classDef framework fill:#bbf,stroke:#333,stroke-width:1px;
    class Controller,SimilarityUtil,EntitySub,DBModels framework;
    
    %% Database Legend
    classDef db fill:#bfb,stroke:#333,stroke-width:1px;
    class CacheEntries,UsageLog db;
```

## Sequence Flow

The sequence diagram below illustrates the flow of a user query through the system, from input to retrieving or generating a response.

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend API
    participant C as Controller
    participant S as Similarity Search
    participant D as Database
    participant L as LLM Service
    U->>F: Enter NL Query
    F->>B: Send Query Request
    B->>C: Process Request
    C->>S: Perform Similarity Search
    S->>D: Retrieve Cached Entries
    alt Match Found
        D-->>S: Return Matching Entry
        S-->>C: Return Template
        C-->>B: Return Response
        B-->>F: Display Result
        F-->>U: Show Structured Output
    else No Match
        D-->>S: No Relevant Entry
        S-->>C: No Match
        C->>L: Generate New Template
        L-->>C: Return Generated Template
        C->>D: Cache New Entry with Embedding
        D-->>C: Confirm Storage
        C-->>B: Return Response
        B-->>F: Display Result
        F-->>U: Show Structured Output
    end
```

## Technical Implementation

The framework is implemented using the following technologies:

- **Backend**: 
  - FastAPI for REST API
  - SQLAlchemy for database ORM
  - Sentence-Transformers for vector embeddings
  - PostgreSQL with pgvector for vector storage and similarity search
  - LLM integration for template generation (supports multiple providers)

- **Frontend**:
  - Next.js with React
  - Tailwind CSS for styling
  - ReactFlow for workflow visualization
  - Radix UI components

## Installation

To set up ThinkForge locally, follow these steps:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/rnednur/thinkforge.git
   cd thinkforge
   ```

2. **Backend Setup**:
   - Navigate to the `backend` directory.
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```
   - Set up the database by running the initialization scripts in `dbscripts`.
   - Start the backend server:
     ```bash
     python app.py
     ```

3. **Frontend Setup**:
   - Navigate to the `frontend` directory.
   - Install dependencies:
     ```bash
     npm install
     ```
   - Start the frontend development server:
     ```bash
     npm run dev
     ```
   - Alternatively, you can start the frontend from the root directory:
     ```bash
     npm run dev
     ```

4. **Docker Setup**:
   - You can also use Docker Compose to set up the entire stack:
     ```bash
     docker-compose up
     ```

5. **Environment Configuration**:
   - Ensure you have the necessary environment variables set for database connections and model configurations. Refer to `.env.example` for required variables.

## Usage

- **Access the Application**: Open your browser and navigate to `http://localhost:3000` (or the port specified by your frontend server) to interact with the UI.
- **Cache Management**: Use the dashboard to view, create, edit, or delete cache entries under `/cache-entries`.
- **Query Testing**: Test natural language queries at `/complete-test` to see the matched or generated structured outputs.
- **Bulk Import**: Use the CSV import functionality to bulk load cache entries from CSV files.

## API Reference

The ThinkForge API provides the following endpoints:

- `POST /v1/complete`: Process a natural language query and return the matching structured output
- `GET /v1/cache`: List all cache entries
- `POST /v1/cache`: Create a new cache entry
- `GET /v1/cache/{id}`: Get a specific cache entry
- `PUT /v1/cache/{id}`: Update a cache entry
- `DELETE /v1/cache/{id}`: Delete a cache entry
- `POST /v1/cache/import`: Import cache entries from CSV
- `GET /v1/cache/stats`: Get usage statistics for cache entries

## Future Enhancements

We have planned several future enhancements for the ThinkForge framework:

- Advanced entity extraction with Named Entity Recognition models
- Template versioning and history
- Analytics dashboard for performance monitoring
- Active learning pipeline for template improvement
- Template optimization for better performance
- Advanced security features
- Workflow orchestration capabilities
- API gateway integration
- Template discovery and recommendation system
- Schema inference for databases
- Model fine-tuning for domain-specific applications
- Edge deployment support
- Explainability features
- Integration connectors for various databases and services

For a complete list of planned enhancements, see the `future_enhancements.md` file.

## Contributing

Contributions are welcome! Please follow these steps to contribute:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them with descriptive messages.
4. Push your changes to your fork.
5. Submit a pull request to the main repository with a detailed description of your changes.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions or support, please contact the project maintainer at [maintainer's email or GitHub profile].