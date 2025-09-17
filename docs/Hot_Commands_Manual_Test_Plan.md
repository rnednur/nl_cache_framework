# Hot Commands & Cache Integration - Manual Test Plan

## Overview
This test plan covers all the Hot Commands functionality integrated with ThinkForge, including cache integration, React frontend, Next.js admin frontend, and backend API endpoints.

## Prerequisites

### Environment Setup
1. **Backend Services Running:**
   ```bash
   cd /Users/rnednur/code/nl_cache_framework
   python run_server.py  # FastAPI server on port 8000
   ```

2. **Frontend Services Running:**
   ```bash
   # React Frontend (User Interface)
   cd frontend-react
   npm run dev  # Port 3000

   # Next.js Frontend (Admin Interface)
   cd frontend/app
   npm run dev  # Port 3001 (or next available)
   ```

3. **Database Requirements:**
   - PostgreSQL with ThinkForge schema
   - Hot Commands tables created via hotcommands_models.py
   - Sample cache entries in the database

## Test Plan Structure

### Phase 1: Backend API Testing
### Phase 2: React Frontend Testing (User Interface)
### Phase 3: Next.js Frontend Testing (Admin Interface)
### Phase 4: Integration & End-to-End Testing
### Phase 5: Error Handling & Edge Cases

---

## Phase 1: Backend API Testing

### 1.1 Hot Commands CRUD API
**Test URL Base:** `http://localhost:8000`

#### Test 1.1.1: Get User's Hot Commands
```bash
# Test endpoint
GET http://localhost:8000/api/hot-commands/my

# Expected: 200 OK with array of user's hot commands
# Check: Response includes command_name, display_name, is_public, usage_count, etc.
```

#### Test 1.1.2: Create Hot Command from Cache Entry
```bash
# First, get available cache entries
GET http://localhost:8000/api/cache-entries/available?limit=5

# Then create hot command from a cache entry
POST http://localhost:8000/api/hot-commands/from-cache
Content-Type: application/json

{
  "cache_entry_id": 1,
  "command_name": "test_command",
  "display_name": "Test Command",
  "description": "Test command description",
  "is_public": false,
  "tags": ["test", "manual"]
}

# Expected: 201 Created with hot command details
```

#### Test 1.1.3: Update Hot Command
```bash
# Get a hot command ID first, then update it
PUT http://localhost:8000/api/hot-commands/{id}
Content-Type: application/json

{
  "display_name": "Updated Test Command",
  "description": "Updated description",
  "is_public": true
}

# Expected: 200 OK with updated command details
```

#### Test 1.1.4: Delete Hot Command
```bash
DELETE http://localhost:8000/api/hot-commands/{id}

# Expected: 204 No Content
```

### 1.2 Cache Integration API

#### Test 1.2.1: Get Available Cache Entries
```bash
GET http://localhost:8000/api/cache-entries/available?template_type=sql&limit=10

# Expected: 200 OK with cache entries that can be converted to hot commands
# Check: has_hot_command field indicates if already converted
```

#### Test 1.2.2: Get Cache Entry Details
```bash
GET http://localhost:8000/api/cache-entries/{id}/details

# Expected: 200 OK with detailed cache entry information
# Check: Includes template, metadata, performance stats
```

### 1.3 Analytics API

#### Test 1.3.1: Dashboard Statistics
```bash
GET http://localhost:8000/api/analytics/dashboard

# Expected: 200 OK with dashboard stats
# Check: total_commands, total_executions, avg_success_rate, popular_commands
```

#### Test 1.3.2: Public Hot Commands
```bash
GET http://localhost:8000/api/hot-commands/public?limit=10

# Expected: 200 OK with public hot commands
# Check: Only returns commands with is_public=true
```

---

## Phase 2: React Frontend Testing (User Interface)

**Access URL:** `http://localhost:3000`

### 2.1 Navigation & Layout

#### Test 2.1.1: Sidebar Navigation
- [ ] Navigate to "Hot Commands" page
- [ ] Navigate to "Spaces" page  
- [ ] Navigate to "Command Builder" page
- [ ] Navigate to "Cache Explorer" page
- [ ] Verify active page highlighting

#### Test 2.1.2: Header & Theme
- [ ] Theme toggle works (light/dark mode)
- [ ] User avatar/menu displays
- [ ] Responsive layout on mobile

### 2.2 Hot Commands Page (`/hot-commands`)

#### Test 2.2.1: Command List Display
- [ ] Commands load and display correctly
- [ ] Command cards show: name, description, usage count, last used
- [ ] Public/private badges display correctly
- [ ] Tags display properly
- [ ] "Create New Command" button visible

#### Test 2.2.2: Search & Filtering
- [ ] Search by command name works
- [ ] Filter by visibility (Public/Private/All) works
- [ ] Filter by domain works
- [ ] Search + filter combination works
- [ ] "Clear filters" functionality

#### Test 2.2.3: Command Actions
- [ ] "View Details" opens command details modal
- [ ] "Edit Command" opens edit dialog
- [ ] "Delete Command" shows confirmation dialog
- [ ] "Execute Command" works (if implemented)

### 2.3 Cache Explorer Page (`/cache-explorer`)

#### Test 2.3.1: Cache Entry Display
- [ ] Cache entries load and display
- [ ] Entry cards show: query, template type, execution stats
- [ ] Health status indicators display correctly
- [ ] "Has Command" badge shows for converted entries

#### Test 2.3.2: Filtering & Search
- [ ] Search by natural language query works
- [ ] Template type filter works (SQL, Workflow, Recipe, etc.)
- [ ] Catalog type filter works
- [ ] "Only available" toggle hides already-converted entries

#### Test 2.3.3: Entry Details & Conversion
- [ ] "View" button opens entry details dialog
- [ ] Details dialog shows: query, template, metadata, performance
- [ ] "Create Command" button available for unconverted entries
- [ ] Command creation dialog pre-fills with entry data
- [ ] Successfully create hot command from cache entry
- [ ] Entry updates to show "Has Command" after conversion

### 2.4 Command Builder Page (`/command-builder`)

#### Test 2.4.1: Form Validation
- [ ] Command name validation (alphanumeric + underscore only)
- [ ] Required field validation
- [ ] Tag input parsing (comma-separated)

#### Test 2.4.2: Command Creation
- [ ] Create new command manually
- [ ] Public/private toggle works
- [ ] Tags save correctly
- [ ] Success message displays
- [ ] Redirects to command list after creation

### 2.5 Spaces Page (`/spaces`)

#### Test 2.5.1: Space Management
- [ ] Spaces list displays
- [ ] Create new space functionality
- [ ] Space cards show member count and commands
- [ ] Access space details

---

## Phase 3: Next.js Frontend Testing (Admin Interface)

**Access URL:** `http://localhost:3001` (or next available port)

### 3.1 Admin Navigation

#### Test 3.1.1: Sidebar Navigation
- [ ] Navigate to "Cache Explorer" 
- [ ] Navigate to "Hot Commands"
- [ ] Navigate to existing pages (Cache Entries, Dashboard, etc.)
- [ ] Verify admin-focused layout and styling

### 3.2 Admin Cache Explorer (`/cache-explorer`)

#### Test 3.2.1: Admin Cache Management
- [ ] All cache entries display with admin-level details
- [ ] Advanced filtering options work
- [ ] Entry details show technical metadata
- [ ] Bulk actions available (if implemented)

#### Test 3.2.2: Admin Command Creation
- [ ] Admin can create hot commands from any cache entry
- [ ] Additional admin fields available
- [ ] Can set public/private permissions
- [ ] Can assign to users (if implemented)

### 3.3 Admin Hot Commands (`/hot-commands`)

#### Test 3.3.1: Admin Command Management
- [ ] View all hot commands (not just user's own)
- [ ] Dashboard statistics display
- [ ] Usage analytics and metrics
- [ ] Admin controls for command management

#### Test 3.3.2: Admin Analytics
- [ ] Total commands, executions, success rates display
- [ ] Popular commands list
- [ ] Recent activity feed
- [ ] Domain usage statistics

---

## Phase 4: Integration & End-to-End Testing

### 4.1 Cross-Platform Consistency

#### Test 4.1.1: Data Synchronization
- [ ] Create hot command in React frontend
- [ ] Verify it appears in Next.js admin interface
- [ ] Update command in admin interface
- [ ] Verify changes reflect in React frontend

#### Test 4.1.2: Cache Entry Integration
- [ ] Convert cache entry to hot command in React
- [ ] Verify "has_hot_command" status updates in admin
- [ ] Check source cache entry link works from admin

### 4.2 API Integration Flow

#### Test 4.2.1: Complete Workflow
1. [ ] Browse cache entries in React frontend
2. [ ] Convert cache entry to hot command
3. [ ] Execute hot command (if implemented)
4. [ ] View execution results
5. [ ] Check analytics in admin interface
6. [ ] Edit command in admin interface
7. [ ] Verify changes in React frontend

### 4.3 Performance Testing

#### Test 4.3.1: Load Testing
- [ ] Load 100+ cache entries - check performance
- [ ] Load 50+ hot commands - check performance  
- [ ] Search/filter with large datasets
- [ ] Pagination works correctly

---

## Phase 5: Error Handling & Edge Cases

### 5.1 Error Scenarios

#### Test 5.1.1: API Error Handling
- [ ] Backend server down - proper error messages
- [ ] Invalid API responses - graceful degradation
- [ ] Network timeouts - retry mechanisms
- [ ] Permission denied - appropriate error display

#### Test 5.1.2: Form Validation Errors
- [ ] Duplicate command names - show error
- [ ] Invalid characters in command name - prevent submission
- [ ] Missing required fields - highlight errors
- [ ] Invalid cache entry ID - show meaningful error

#### Test 5.1.3: Edge Cases
- [ ] Empty cache entries list - show empty state
- [ ] No hot commands - show getting started message
- [ ] Very long command names/descriptions - handle gracefully
- [ ] Special characters in tags - parse correctly

### 5.2 Browser Compatibility

#### Test 5.2.1: Cross-Browser Testing
- [ ] Chrome - full functionality
- [ ] Firefox - full functionality  
- [ ] Safari - full functionality
- [ ] Edge - full functionality

#### Test 5.2.2: Responsive Design
- [ ] Mobile phone layout (320px-767px)
- [ ] Tablet layout (768px-1023px)
- [ ] Desktop layout (1024px+)
- [ ] Touch interactions work on mobile

---

## Test Execution Checklist

### Before Testing
- [ ] All services running (Backend, React, Next.js)
- [ ] Database has sample data
- [ ] Clear browser cache/cookies
- [ ] Open browser developer tools

### During Testing
- [ ] Check browser console for errors
- [ ] Monitor network requests in dev tools
- [ ] Note any performance issues
- [ ] Screenshot any visual bugs
- [ ] Document steps to reproduce issues

### After Testing
- [ ] Clean up test data
- [ ] Document all found issues
- [ ] Verify critical path functionality
- [ ] Report results with evidence

---

## Expected Test Results

### Success Criteria
- [ ] All critical functionality works without errors
- [ ] Data consistency between React and Next.js frontends
- [ ] Proper error handling and user feedback
- [ ] Responsive design works across devices
- [ ] Performance is acceptable for expected load

### Known Issues to Verify Fixed
- [ ] SelectItem empty string values (should use 'all')
- [ ] Lucide React FileTemplate icon (should use FileText)
- [ ] Pydantic datetime validation (should handle datetime objects)
- [ ] Hot Commands foreign key constraints (should work without FK)

---

## Reporting Template

```markdown
## Test Execution Report - [Date]

### Environment
- Backend: [Status/Version]
- React Frontend: [Status/Version] 
- Next.js Frontend: [Status/Version]
- Database: [Status/Version]

### Test Results Summary
- Total Tests: [X]
- Passed: [X]
- Failed: [X]
- Blocked: [X]

### Critical Issues Found
1. [Issue description with steps to reproduce]
2. [Issue description with steps to reproduce]

### Minor Issues Found
1. [Issue description]
2. [Issue description]

### Performance Notes
- [Any performance observations]

### Recommendations
- [Any recommendations for improvements]
```

This comprehensive test plan should help you systematically verify all the Hot Commands and cache integration functionality across both frontends and the backend API.