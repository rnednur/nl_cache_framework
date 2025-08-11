#!/usr/bin/env python3
"""
DSL Query Builder Demo

This script demonstrates how DSL components can be retrieved from the ThinkForge
cache and composed together to build complex database queries.
"""

import json
from typing import Dict, List, Any, Optional


class DSLQueryBuilder:
    """
    Utility class to build SQL queries from DSL components stored in ThinkForge cache.
    """
    
    def __init__(self, cache_controller):
        """
        Initialize the DSL Query Builder with a ThinkForge controller.
        
        Args:
            cache_controller: An instance of Text2SQLController
        """
        self.controller = cache_controller
        
    def find_dsl_components(self, query_parts: List[str]) -> List[Dict[str, Any]]:
        """
        Search for DSL components matching the given query parts.
        
        Args:
            query_parts: List of natural language descriptions of needed components
            
        Returns:
            List of matching DSL components from the cache
        """
        components = []
        
        for query_part in query_parts:
            # Search for DSL components matching this part
            matches = self.controller.search_query(
                nl_query=query_part,
                template_type="dsl",
                similarity_threshold=0.7,
                limit=1
            )
            
            if matches:
                components.extend(matches)
                
        return components
    
    def build_sql_from_components(self, components: List[Dict[str, Any]]) -> str:
        """
        Build a SQL query from a list of DSL components.
        
        Args:
            components: List of DSL components
            
        Returns:
            Generated SQL query string
        """
        # Parse components by type
        tables = []
        columns = []
        joins = []
        filters = []
        aggregates = []
        group_bys = []
        order_bys = []
        limits = []
        
        for component in components:
            template_data = json.loads(component['template']) if isinstance(component['template'], str) else component['template']
            component_type = template_data.get('component_type')
            component_data = template_data.get('component_data', {})
            
            if component_type == 'TABLE':
                tables.append(component_data.get('table_name'))
            elif component_type == 'COLUMN':
                columns.append(component_data.get('qualified_name') or 
                             f"{component_data.get('table_name')}.{component_data.get('column_name')}")
            elif component_type == 'JOIN':
                joins.append(f"{component_data.get('join_type', 'INNER')} JOIN {component_data.get('right_table')} ON {component_data.get('join_condition')}")
            elif component_type == 'FILTER':
                filters.append(component_data.get('filter_condition'))
            elif component_type == 'AGGREGATE':
                aggregates.append(f"{component_data.get('expression')} AS {component_data.get('alias')}")
            elif component_type == 'GROUP_BY':
                group_bys.append(component_data.get('group_expression'))
            elif component_type == 'ORDER_BY':
                order_bys.append(component_data.get('order_expression'))
            elif component_type == 'LIMIT':
                limits.append(str(component_data.get('limit_count')))
        
        # Build SQL query
        sql_parts = []
        
        # SELECT clause
        select_items = columns + aggregates if columns or aggregates else ['*']
        sql_parts.append(f"SELECT {', '.join(select_items)}")
        
        # FROM clause
        if tables:
            sql_parts.append(f"FROM {tables[0]}")
        
        # JOIN clauses
        for join in joins:
            sql_parts.append(join)
        
        # WHERE clause
        if filters:
            sql_parts.append(f"WHERE {' AND '.join(filters)}")
        
        # GROUP BY clause
        if group_bys:
            sql_parts.append(f"GROUP BY {', '.join(group_bys)}")
        
        # ORDER BY clause
        if order_bys:
            sql_parts.append(f"ORDER BY {', '.join(order_bys)}")
        
        # LIMIT clause
        if limits:
            sql_parts.append(f"LIMIT {limits[0]}")
        
        return '\n'.join(sql_parts)
    
    def build_query_from_natural_language(self, nl_query: str, component_hints: List[str]) -> str:
        """
        Build a SQL query from natural language using DSL components.
        
        Args:
            nl_query: Natural language description of the desired query
            component_hints: List of component descriptions to search for
            
        Returns:
            Generated SQL query string
        """
        print(f"Building query for: {nl_query}")
        print(f"Searching for components: {component_hints}")
        
        # Find relevant DSL components
        components = self.find_dsl_components(component_hints)
        
        if not components:
            print("No matching DSL components found")
            return ""
        
        print(f"Found {len(components)} matching components:")
        for comp in components:
            print(f"  - {comp['nl_query']} (similarity: {comp.get('similarity', 'N/A')})")
        
        # Build SQL from components
        sql_query = self.build_sql_from_components(components)
        
        print(f"\nGenerated SQL:\n{sql_query}")
        return sql_query


def demo_dsl_query_building():
    """
    Demonstrate DSL query building with example scenarios.
    """
    print("=== DSL Query Builder Demo ===\n")
    
    # Example scenarios
    scenarios = [
        {
            "description": "Get active users with their order counts",
            "components": [
                "users table",
                "user email column", 
                "join users with orders",
                "filter active users",
                "count total orders",
                "group by user"
            ]
        },
        {
            "description": "Recent high-value orders",
            "components": [
                "orders table",
                "sum order amounts",
                "filter orders above 100",
                "order by recent first",
                "limit to 10 results"
            ]
        },
        {
            "description": "User activity in date range",
            "components": [
                "users table",
                "join users with orders", 
                "date range filter for :start_date to :end_date",
                "count total orders",
                "group by user",
                "order by recent first"
            ]
        }
    ]
    
    print("Example DSL Query Building Scenarios:")
    print("=" * 50)
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['description']}")
        print(f"   Components needed: {', '.join(scenario['components'])}")
        print(f"   → This would search the cache for these DSL components")
        print(f"   → Then compose them into a complete SQL query")
    
    print("\n" + "=" * 50)
    print("Benefits of DSL Components:")
    print("• Reusable query building blocks")
    print("• Semantic search for relevant components") 
    print("• Consistent query patterns across applications")
    print("• Easy composition of complex queries")
    print("• Better caching and optimization opportunities")


if __name__ == "__main__":
    demo_dsl_query_building() 