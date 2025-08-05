# Catalog Management Guide

## Overview

This guide explains how to effectively manage catalog types, subtypes, and names in the ThinkForge system, including best practices for handling large datasets and organizing your tools and recipes.

## Features

### Dropdown Functionality
- **Dynamic Loading**: Catalog values are fetched from existing database entries
- **Search and Filter**: Quickly find existing options with real-time search
- **Add New Options**: Create new catalog values inline without leaving the form
- **Performance Optimized**: Handles large datasets with pagination and search

### Component Usage

The `CatalogSelect` component provides:
- Dropdown with existing values from the database
- Search functionality to filter large lists
- Ability to add new custom values
- Performance optimizations for handling 100+ options

```tsx
<CatalogSelect
  catalogField="catalog_type"
  label="Catalog Type"
  value={catalogType}
  onValueChange={setCatalogType}
  placeholder="Select catalog type..."
  allowCustom={true}
  maxDisplayItems={100}
/>
```

## Best Practices for Large Datasets

### 1. Hierarchical Organization

Use a hierarchical structure for your catalog organization:

```
catalog_type (High-level category)
├── catalog_subtype (Sub-category) 
    └── catalog_name (Specific item)
```

**Example Structure:**
```
database
├── mysql
    ├── customer_queries
    ├── order_queries
    └── inventory_queries
├── postgres
    ├── analytics_queries
    ├── reporting_queries
    └── user_queries
└── mongodb
    ├── document_operations
    ├── aggregation_pipelines
    └── indexing_operations
```

### 2. Naming Conventions

#### Catalog Types (10-20 options recommended)
- Use broad technology categories
- Examples: `database`, `api`, `workflow`, `ml_model`, `data_processing`

#### Catalog Subtypes (20-50 per type recommended)  
- Use specific technology or domain areas
- Examples: `mysql`, `postgres`, `rest_api`, `graphql`, `data_pipeline`

#### Catalog Names (50-200 per subtype recommended)
- Use descriptive, specific names
- Examples: `customer_lookup`, `order_processing`, `payment_validation`

### 3. Performance Optimization Strategies

#### Search and Pagination
- **Default Display**: 100 items shown initially
- **Real-time Search**: Filters as you type
- **Smart Sorting**: Exact matches and prefix matches prioritized
- **Lazy Loading**: Additional items loaded on demand

#### Component Configuration
```tsx
// For very large datasets
<CatalogSelect
  maxDisplayItems={50}  // Reduce initial load
  // ... other props
/>

// For smaller, frequently used datasets
<CatalogSelect
  maxDisplayItems={200} // Show more options
  // ... other props
/>
```

### 4. Data Management Strategies

#### Regular Cleanup
- Periodically review and consolidate similar entries
- Remove unused or obsolete catalog values
- Standardize naming conventions

#### Bulk Management
Use database scripts for bulk operations:

```sql
-- Find duplicate or similar entries
SELECT catalog_type, catalog_subtype, catalog_name, COUNT(*)
FROM text2sql_cache 
GROUP BY catalog_type, catalog_subtype, catalog_name
HAVING COUNT(*) > 1;

-- Standardize naming (example)
UPDATE text2sql_cache 
SET catalog_type = 'database'
WHERE catalog_type IN ('db', 'Database', 'databases');
```

### 5. Organizational Recommendations

#### For Small Teams (< 50 tools/recipes)
- Keep it simple with 5-10 catalog types
- Use descriptive, self-explanatory names
- Focus on functional categorization

#### For Medium Teams (50-200 tools/recipes)
- Implement clear naming conventions
- Use 10-20 catalog types with consistent subtypes
- Regular review and cleanup sessions

#### For Large Teams (200+ tools/recipes)
- Establish governance policies
- Implement automated validation
- Use standardized taxonomies
- Regular audits and consolidation

### 6. Advanced Features

#### Search Optimization
The component includes intelligent search features:
- **Prefix matching**: Items starting with search term appear first
- **Substring matching**: All items containing the search term
- **Case-insensitive**: Works regardless of capitalization
- **Deduplication**: Prevents duplicate entries

#### Custom Value Addition
Two ways to add new values:
1. **Quick Add**: Type in search box and select "Add [value]"
2. **Form Add**: Click "Add new option..." for guided entry

#### Performance Monitoring
```tsx
// Enable performance tracking
<CatalogSelect
  catalogField="catalog_type"
  maxDisplayItems={100}
  // Performance will automatically degrade gracefully
  // if dataset becomes very large
/>
```

## API Integration

### Automatic Data Loading
The component automatically fetches catalog values from:
- `/v1/catalog/values` - Returns all unique catalog values
- Caches results for session duration
- Refreshes on component mount

### Adding New Values
When users add new values:
1. Component adds to local state immediately
2. Value is saved when parent form is submitted
3. Becomes available to other users on next page load

## Troubleshooting

### Performance Issues
If dropdowns become slow with very large datasets:

1. **Reduce maxDisplayItems**:
   ```tsx
   <CatalogSelect maxDisplayItems={25} />
   ```

2. **Implement hierarchical filtering**:
   Filter subtypes based on selected type, names based on selected subtype

3. **Consider data archival**:
   Move old/unused entries to archive status

### Memory Usage
For extremely large datasets (1000+ items per field):
- Consider implementing virtual scrolling
- Use server-side search instead of client-side filtering
- Implement lazy loading with pagination

## Migration Guide

### From Text Inputs
If migrating from existing text input fields:

1. Install new components (already done)
2. Replace Input components with CatalogSelect
3. Update value handlers to support undefined values
4. Test with existing data

### Data Validation
Existing data will work seamlessly:
- All existing catalog values appear in dropdowns
- Users can still enter custom values
- No data migration required

## Future Enhancements

Planned improvements:
- **Server-side search** for very large datasets
- **Bulk import/export** of catalog taxonomies
- **Usage analytics** to identify popular/unused values
- **Auto-suggestions** based on usage patterns
- **Team-specific** catalog organization 