# ThinkForge Spaces Implementation Plan

## Phase 1: Enhanced Space Model (Week 1)

### 1.1 Update Space Model in `thinkforge/hotcommands_models.py`

**Add Missing Enums:**
```python
class StorageBackend(str, Enum):
    LOCAL = "local"
    S3 = "s3" 
    GCS = "gcs"
    AZURE = "azure"

class ScheduleType(str, Enum):
    NONE = "none"
    INTERVAL = "interval"
    CRON = "cron"
    WEBHOOK = "webhook"

# Add to ContentType enum:
TEMPLATE = "template"
WEBPAGE = "webpage"
```

**Add Missing Fields to Space Model:**
```python
# Template functionality
is_template = Column(Boolean, default=False, nullable=False, index=True)
template_parameters = Column(JSONB, nullable=True)
template_schema = Column(JSONB, nullable=True)
base_query = Column(Text, nullable=True)
source_query = Column(Text, nullable=True)

# External storage
storage_path = Column(String(500), nullable=True)
storage_backend = Column(String(20), default=StorageBackend.LOCAL, nullable=False)
storage_size_bytes = Column(Integer, default=0, nullable=False)
external_url = Column(String(1000), nullable=True)

# Scheduling
schedule_type = Column(String(20), default=ScheduleType.NONE, nullable=False)
schedule_config = Column(JSONB, nullable=True)
next_execution = Column(DateTime(timezone=True), nullable=True, index=True)
last_execution = Column(DateTime(timezone=True), nullable=True, index=True)
execution_count = Column(Integer, default=0, nullable=False)
is_scheduled_active = Column(Boolean, default=False, nullable=False, index=True)

# Enhanced sharing
access_permissions = Column(JSONB, nullable=True)
team_id = Column(String(100), nullable=True, index=True)

# Expiration
expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
auto_cleanup = Column(Boolean, default=False, nullable=False)
retention_days = Column(Integer, nullable=True)
```

### 1.2 Add SpaceAccess Model for Granular Permissions

```python
class AccessLevel(str, Enum):
    VIEW = "view"
    COMMENT = "comment" 
    EDIT = "edit"
    ADMIN = "admin"

class SpaceAccess(Base):
    __tablename__ = "space_access"
    __table_args__ = table_args
    
    id = Column(Integer, primary_key=True, index=True)
    space_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.spaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey(f"{DB_SCHEMA}.users.id"), nullable=False, index=True)
    granted_by = Column(Integer, ForeignKey(f"{DB_SCHEMA}.users.id"), nullable=False)
    
    access_level = Column(String(20), default=AccessLevel.VIEW, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    access_count = Column(Integer, default=0, nullable=False)
    last_accessed = Column(DateTime(timezone=True), nullable=True, index=True)
    restrictions = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    space = relationship("Space", backref="access_grants")
    user = relationship("User", foreign_keys=[user_id])
    grantor = relationship("User", foreign_keys=[granted_by])
```

### 1.3 Add Model Methods to Space Class

```python
def is_template_space(self) -> bool:
    return self.is_template and self.content_type == ContentType.TEMPLATE

def validate_template_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
    # Parameter validation logic
    pass

def render_template_query(self, params: Dict[str, Any]) -> str:
    # Template rendering logic
    pass

def schedule_next_execution(self) -> Optional[datetime.datetime]:
    # Calculate next execution time
    pass

def can_be_accessed_by(self, user_id: int, access_level: AccessLevel = AccessLevel.VIEW) -> bool:
    # Access control logic
    pass
```

## Phase 2: Storage Service Integration (Week 1-2)

### 2.1 Create Storage Service in `thinkforge/storage_service.py`

**Multi-backend Storage Support:**
```python
class StorageService:
    def __init__(self):
        self.backends = {
            StorageBackend.LOCAL: LocalStorageBackend(),
            StorageBackend.S3: S3StorageBackend() if boto3_available else None,
            StorageBackend.GCS: GCSStorageBackend() if gcs_available else None,
        }
    
    def upload_space_content(self, space_id: int, content: bytes, 
                           backend: StorageBackend, content_type: str) -> Tuple[str, str]:
        # Upload and return (storage_path, public_url)
        pass
    
    def upload_webpage_export(self, space_id: int, html_content: str, 
                            backend: StorageBackend) -> Tuple[str, str]:
        # Export as shareable webpage
        pass
```

### 2.2 Update requirements.txt

```text
# Add to backend/requirements.txt
croniter>=2.0.1
boto3>=1.34.0  # Optional for S3
google-cloud-storage>=2.13.0  # Optional for GCS
azure-storage-blob>=12.19.0  # Optional for Azure
```

## Phase 3: API Endpoints (Week 2)

### 3.1 Add Spaces Router to `backend/app.py`

**Core Endpoints:**
```python
# Add to app.py imports
from .services.spaces_service import SpacesService

@app.get("/v1/spaces", tags=["spaces"])
async def list_spaces(
    skip: int = 0,
    limit: int = 100,
    space_type: Optional[SpaceType] = None,
    content_type: Optional[ContentType] = None,
    is_template: Optional[bool] = None,
    my_spaces: bool = False,
    shared_with_me: bool = False,
    db: Session = Depends(get_db)
):
    # List spaces with filtering
    pass

@app.post("/v1/spaces", tags=["spaces"])
async def create_space(space_data: SpaceCreate, db: Session = Depends(get_db)):
    # Create new space
    pass

@app.get("/v1/spaces/{space_id}", tags=["spaces"])
async def get_space(space_id: int, db: Session = Depends(get_db)):
    # Get specific space
    pass

@app.put("/v1/spaces/{space_id}", tags=["spaces"])
async def update_space(space_id: int, space_update: SpaceUpdate, db: Session = Depends(get_db)):
    # Update space
    pass

@app.delete("/v1/spaces/{space_id}", tags=["spaces"])
async def delete_space(space_id: int, db: Session = Depends(get_db)):
    # Soft delete space
    pass

@app.post("/v1/spaces/{space_id}/execute", tags=["spaces"])
async def execute_space(space_id: int, execute_request: TemplateExecuteRequest, db: Session = Depends(get_db)):
    # Execute template or re-run space
    pass

@app.post("/v1/spaces/{space_id}/share", tags=["spaces"])
async def share_space(space_id: int, share_request: SpaceShareRequest, db: Session = Depends(get_db)):
    # Share space with users
    pass

@app.post("/v1/spaces/{space_id}/upload", tags=["spaces"])
async def upload_space_content(space_id: int, file: UploadFile, storage_backend: StorageBackend, db: Session = Depends(get_db)):
    # Upload content to space
    pass

@app.get("/v1/spaces/{space_id}/export-url", tags=["spaces"])
async def get_export_url(space_id: int, expires_in: int = 3600, db: Session = Depends(get_db)):
    # Get public sharing URL
    pass
```

### 3.2 Create Pydantic Schemas

**Create `backend/schemas/spaces.py`:**
```python
class SpaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = None
    description: Optional[str] = None
    space_type: SpaceType = SpaceType.PERSONAL
    content_type: ContentType = ContentType.QUERY_RESULT
    domain: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    is_public: bool = False

class SpaceCreate(SpaceBase):
    is_template: bool = False
    template_parameters: Optional[List[Dict[str, Any]]] = None
    base_query: Optional[str] = None
    content_data: Optional[Dict[str, Any]] = None
    storage_backend: StorageBackend = StorageBackend.LOCAL
    schedule_type: ScheduleType = ScheduleType.NONE
    schedule_config: Optional[Dict[str, Any]] = None

class SpaceResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    description: Optional[str]
    space_type: SpaceType
    content_type: ContentType
    is_template: bool
    is_active: bool
    is_public: bool
    owner_id: int
    storage_backend: StorageBackend
    external_url: Optional[str]
    view_count: int
    share_count: int
    execution_count: int
    schedule_type: ScheduleType
    is_scheduled_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TemplateExecuteRequest(BaseModel):
    parameters: Dict[str, Any]
    save_result: bool = False
    result_name: Optional[str] = None
```

## Phase 4: Business Logic Service (Week 2-3)

### 4.1 Create `thinkforge/spaces_service.py`

**Core Business Logic:**
```python
class SpacesService:
    def __init__(self, db: Session):
        self.db = db
        self.storage_service = StorageService()
        
    async def execute_template(self, space: Space, parameters: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        # Validate parameters
        validation = space.validate_template_params(parameters)
        if not validation['valid']:
            raise SpaceExecutionError(f"Invalid parameters: {', '.join(validation['errors'])}")
        
        # Render template query
        rendered_query = space.render_template_query(parameters)
        
        # Execute query using ThinkForge controller
        controller = Text2SQLController()
        result = await controller.complete(rendered_query, user_id=user_id)
        
        # Store result if needed
        execution_result = {
            'query': rendered_query,
            'parameters': parameters,
            'result': result,
            'execution_time': result.get('execution_time_ms', 0)
        }
        
        return execution_result
    
    async def execute_space(self, space: Space, user_id: int) -> Dict[str, Any]:
        # Re-execute saved query
        query = space.source_query or space.base_query
        controller = Text2SQLController()
        result = await controller.complete(query, user_id=user_id)
        
        # Update space content
        space.content_data = result
        space.execution_count += 1
        space.last_execution = datetime.utcnow()
        
        return result
    
    def create_template_from_cache_entry(self, cache_entry_id: int, space_name: str, owner_id: int) -> Space:
        # Convert ThinkForge cache entry to template space
        pass
    
    async def schedule_space_execution(self, space: Space) -> bool:
        # Schedule with Celery or background tasks
        pass
```

### 4.2 Integration with ThinkForge Controller

**Enhance `thinkforge/controller.py` to support spaces:**
```python
class Text2SQLController:
    def create_space_from_cache_entry(self, cache_id: int, space_name: str, user_id: int) -> Space:
        """Convert cache entry to reusable space."""
        cache_entry = self.get_cache_entry(cache_id)
        
        space = Space(
            owner_id=user_id,
            name=space_name,
            content_type=ContentType.QUERY_RESULT,
            source_query=cache_entry.template,
            domain=cache_entry.domain,
            category=cache_entry.category,
            content_data=cache_entry.execution_config,
            content_metadata={
                'cache_entry_id': cache_id,
                'original_template_type': cache_entry.template_type,
                'similarity_score': cache_entry.similarity_score
            }
        )
        
        # If it has parameters, make it a template
        if cache_entry.entity_replacements:
            space.is_template = True
            space.template_parameters = self._extract_template_parameters(cache_entry)
            space.content_type = ContentType.TEMPLATE
        
        return space
```

## Phase 5: Frontend Integration (Week 3)

### 5.1 Update `frontend-react/src/services/api.ts`

**Add Spaces API Client:**
```typescript
// Add to api.ts
export const spacesApi = {
  getSpaces: async (params?: {
    skip?: number;
    limit?: number;
    space_type?: string;
    content_type?: string;
    is_template?: boolean;
    my_spaces?: boolean;
    shared_with_me?: boolean;
  }) => {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          queryParams.append(key, value.toString());
        }
      });
    }
    return apiCall(`/v1/spaces?${queryParams}`);
  },

  createSpace: async (spaceData: SpaceCreate) => {
    return apiCall('/v1/spaces', {
      method: 'POST',
      body: JSON.stringify(spaceData),
    });
  },

  getSpace: async (spaceId: number) => {
    return apiCall(`/v1/spaces/${spaceId}`);
  },

  updateSpace: async (spaceId: number, spaceData: Partial<SpaceCreate>) => {
    return apiCall(`/v1/spaces/${spaceId}`, {
      method: 'PUT',
      body: JSON.stringify(spaceData),
    });
  },

  deleteSpace: async (spaceId: number) => {
    return apiCall(`/v1/spaces/${spaceId}`, {
      method: 'DELETE',
    });
  },

  executeSpace: async (spaceId: number, executeRequest: TemplateExecuteRequest) => {
    return apiCall(`/v1/spaces/${spaceId}/execute`, {
      method: 'POST',
      body: JSON.stringify(executeRequest),
    });
  },

  shareSpace: async (spaceId: number, shareRequest: SpaceShareRequest) => {
    return apiCall(`/v1/spaces/${spaceId}/share`, {
      method: 'POST',
      body: JSON.stringify(shareRequest),
    });
  },

  uploadContent: async (spaceId: number, file: File, storageBackend: string = 'local') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('storage_backend', storageBackend);
    
    return apiCall(`/v1/spaces/${spaceId}/upload`, {
      method: 'POST',
      body: formData,
    });
  },

  getExportUrl: async (spaceId: number, expiresIn: number = 3600) => {
    return apiCall(`/v1/spaces/${spaceId}/export-url?expires_in=${expiresIn}`);
  },
};
```

### 5.2 Update `frontend-react/src/pages/Spaces.tsx`

**Replace Mock Data with Real API Calls:**
```typescript
import { spacesApi } from '../services/api';

export default function Spaces() {
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSpaces = async () => {
      try {
        setLoading(true);
        const response = await spacesApi.getSpaces();
        setSpaces(response.spaces || []);
      } catch (err) {
        setError('Failed to load spaces');
        console.error('Error loading spaces:', err);
      } finally {
        setLoading(false);
      }
    };

    loadSpaces();
  }, []);

  const handleCreateSpace = async () => {
    // Navigate to create space form or open modal
  };

  const handleExecuteSpace = async (spaceId: number, parameters?: any) => {
    try {
      const result = await spacesApi.executeSpace(spaceId, { parameters: parameters || {} });
      // Handle execution result
    } catch (err) {
      console.error('Execution failed:', err);
    }
  };

  // Rest of component logic...
}
```

### 5.3 Create Space Management Components

**Create `frontend-react/src/components/spaces/`:**
```
- SpaceCreateForm.tsx
- SpaceDetailModal.tsx
- TemplateParameterForm.tsx
- SpaceExecutionDialog.tsx
- SpaceShareDialog.tsx
- ExternalStorageSettings.tsx
- ScheduleConfigForm.tsx
```

## Phase 6: Database Migration (Week 3)

### 6.1 Create Migration Script

**Create `dbscripts/add_spaces_enhancements.sql`:**
```sql
-- Add new enums
ALTER TYPE space_type ADD VALUE IF NOT EXISTS 'temporary';

-- Add new content types
INSERT INTO content_types VALUES 
  ('template'), 
  ('webpage') 
ON CONFLICT DO NOTHING;

-- Add new columns to spaces table
ALTER TABLE spaces 
ADD COLUMN IF NOT EXISTS is_template BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS template_parameters JSONB,
ADD COLUMN IF NOT EXISTS template_schema JSONB,
ADD COLUMN IF NOT EXISTS base_query TEXT,
ADD COLUMN IF NOT EXISTS source_query TEXT,
ADD COLUMN IF NOT EXISTS storage_path VARCHAR(500),
ADD COLUMN IF NOT EXISTS storage_backend VARCHAR(20) DEFAULT 'local' NOT NULL,
ADD COLUMN IF NOT EXISTS storage_size_bytes INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS external_url VARCHAR(1000),
ADD COLUMN IF NOT EXISTS schedule_type VARCHAR(20) DEFAULT 'none' NOT NULL,
ADD COLUMN IF NOT EXISTS schedule_config JSONB,
ADD COLUMN IF NOT EXISTS next_execution TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS last_execution TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS execution_count INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS is_scheduled_active BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS access_permissions JSONB,
ADD COLUMN IF NOT EXISTS team_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS auto_cleanup BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS retention_days INTEGER;

-- Create space_access table
CREATE TABLE IF NOT EXISTS space_access (
    id SERIAL PRIMARY KEY,
    space_id INTEGER NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    granted_by INTEGER NOT NULL REFERENCES users(id),
    access_level VARCHAR(20) DEFAULT 'view' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    access_count INTEGER DEFAULT 0 NOT NULL,
    last_accessed TIMESTAMP WITH TIME ZONE,
    restrictions JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Add indexes
CREATE INDEX IF NOT EXISTS ix_spaces_template ON spaces(is_template, is_active);
CREATE INDEX IF NOT EXISTS ix_spaces_scheduled ON spaces(is_scheduled_active, next_execution);
CREATE INDEX IF NOT EXISTS ix_spaces_storage_backend ON spaces(storage_backend);
CREATE INDEX IF NOT EXISTS ix_space_access_space_user ON space_access(space_id, user_id);
CREATE INDEX IF NOT EXISTS ix_space_access_active ON space_access(is_active, expires_at);
```

### 6.2 Create Migration Runner

**Create `dbscripts/migrate_spaces_enhancements.py`:**
```python
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from thinkforge.models import DATABASE_URL
import logging

def run_migration():
    engine = create_engine(DATABASE_URL)
    
    with open('dbscripts/add_spaces_enhancements.sql', 'r') as f:
        migration_sql = f.read()
    
    with engine.connect() as conn:
        conn.execute(text(migration_sql))
        conn.commit()
    
    print("Spaces enhancements migration completed successfully!")

if __name__ == "__main__":
    run_migration()
```

## Phase 7: Advanced Features (Week 4)

### 7.1 LLM Integration for Template Adaptation

**Add to `llm_service.py`:**
```python
class LLMService:
    async def adapt_template(self, template_query: str, parameters: list, 
                           context: str, requirements: str) -> Dict[str, Any]:
        """Adapt template based on new requirements."""
        prompt = f"""
        Adapt this SQL template based on new requirements:
        
        Original: {template_query}
        Parameters: {parameters}
        Context: {context}
        New Requirements: {requirements}
        
        Provide updated query and parameters in JSON format.
        """
        
        response = await self.complete(prompt)
        return json.loads(response)
```

### 7.2 Scheduling Integration

**Add to `thinkforge/scheduler.py`:**
```python
from celery import Celery
import croniter
from datetime import datetime, timedelta

class SpaceScheduler:
    def __init__(self):
        self.celery_app = Celery('thinkforge_scheduler')
    
    def schedule_space_execution(self, space: Space):
        if space.schedule_type == ScheduleType.INTERVAL:
            interval = space.schedule_config.get('interval_minutes', 60)
            eta = datetime.utcnow() + timedelta(minutes=interval)
        elif space.schedule_type == ScheduleType.CRON:
            cron = croniter.croniter(space.schedule_config.get('cron_expression'))
            eta = cron.get_next(datetime)
        
        self.celery_app.send_task('execute_scheduled_space', args=[space.id], eta=eta)
```

### 7.3 Integration with Cache Entries

**Add methods to connect spaces with ThinkForge cache:**
```python
@app.post("/v1/cache/{cache_id}/create-space", tags=["spaces"])
async def create_space_from_cache(cache_id: int, space_name: str, db: Session = Depends(get_db)):
    """Convert cache entry to reusable space."""
    controller = Text2SQLController()
    space = controller.create_space_from_cache_entry(cache_id, space_name, user_id=1)  # TODO: get from auth
    
    db.add(space)
    db.commit()
    db.refresh(space)
    
    return SpaceResponse.from_orm(space)
```

## Testing & Validation

### Unit Tests
```python
# tests/test_spaces.py
def test_create_space():
    pass

def test_execute_template():
    pass

def test_space_permissions():
    pass

def test_external_storage():
    pass
```

### Integration Tests
```python
# tests/test_spaces_integration.py
def test_spaces_api_endpoints():
    pass

def test_cache_to_space_conversion():
    pass

def test_scheduled_execution():
    pass
```

## Deployment Checklist

- [ ] Update `requirements.txt` with new dependencies
- [ ] Run database migrations
- [ ] Configure external storage (optional)
- [ ] Set up Celery for scheduling (optional)
- [ ] Update frontend build process
- [ ] Add API documentation
- [ ] Create user documentation
- [ ] Set up monitoring for scheduled tasks

## Benefits of This Approach

1. **Builds on ThinkForge**: Leverages existing cache system and similarity search
2. **Incremental**: Can be implemented in phases
3. **Backward Compatible**: Doesn't break existing functionality
4. **Scalable**: Uses proven PostgreSQL + FastAPI + React stack
5. **Integrated**: Spaces connect naturally with ThinkForge cache entries
6. **Flexible**: Supports templates, scheduling, and external storage
7. **Production Ready**: Includes proper testing, migrations, and deployment plan

This implementation plan provides a comprehensive roadmap for adding full spaces functionality to ThinkForge while leveraging its existing architecture and maintaining compatibility with the current system.