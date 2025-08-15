"""
Recipe Tool Mapper for ThinkForge

This module provides intelligent mapping between recipe steps and available tools
using semantic similarity, context awareness, and confidence scoring.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from sqlalchemy.orm import Session

from .recipe_step_analyzer import ParsedStep, StepType
from .controller import Text2SQLController
from .models import Text2SQLCache, TemplateType

logger = logging.getLogger(__name__)

# Configuration flag for tool mapping approach
USE_LEGACY_TOOL_MAPPING = False  # Set to True to use the old complex multi-phase search


@dataclass
class ToolMatch:
    """Represents a potential tool match for a recipe step."""
    tool_id: int
    tool_name: str
    tool_type: str
    similarity_score: float
    context_score: float
    compatibility_score: float
    overall_confidence: float
    reasoning: str
    tool_capabilities: List[str]
    tool_data: Dict[str, Any]


@dataclass
class StepMapping:
    """Represents the mapping result for a single recipe step."""
    step_id: str
    step: ParsedStep
    matches: List[ToolMatch]
    best_match: Optional[ToolMatch]
    mapping_confidence: float
    requires_manual_review: bool
    suggestions: List[str]


class MappingStrategy(str, Enum):
    """Different strategies for mapping steps to tools."""
    SEMANTIC_ONLY = "semantic_only"        # Pure semantic similarity
    CONTEXTUAL = "contextual"              # Include step context and type
    CAPABILITY_BASED = "capability_based"  # Focus on tool capabilities
    HYBRID = "hybrid"                      # Combine all approaches


class RecipeToolMapper:
    """
    Intelligent mapper that matches recipe steps to available tools using
    semantic similarity, contextual understanding, and capability matching.
    """
    
    def __init__(self, db_session: Session, controller: Text2SQLController):
        """
        Initialize the recipe tool mapper.
        
        Args:
            db_session: Database session for tool queries
            controller: ThinkForge controller for similarity search
        """
        self.session = db_session
        self.controller = controller
        self.mapping_thresholds = self._get_mapping_thresholds()
        self.step_type_mappings = self._get_step_type_tool_mappings()
        
    def map_recipe_to_tools(
        self, 
        steps: List[ParsedStep], 
        strategy: MappingStrategy = MappingStrategy.HYBRID,
        similarity_threshold: float = 0.3,
        max_matches_per_step: int = 5,
        catalog_filters: Dict[str, str] = None
    ) -> List[StepMapping]:
        """
        Map all recipe steps to available tools.
        
        Args:
            steps: List of parsed recipe steps
            strategy: Mapping strategy to use
            similarity_threshold: Minimum similarity score for matches
            max_matches_per_step: Maximum number of tool matches per step
            catalog_filters: Optional catalog filtering (catalog_type, catalog_subtype, catalog_name)
            
        Returns:
            List of step mappings with tool matches
        """
        logger.info(f"Mapping {len(steps)} recipe steps to tools using {strategy} strategy")
        
        mappings = []
        
        for step in steps:
            try:
                mapping = self._map_single_step(
                    step, 
                    strategy, 
                    similarity_threshold, 
                    max_matches_per_step,
                    catalog_filters
                )
                mappings.append(mapping)
                
            except Exception as e:
                logger.error(f"Failed to map step {step.id}: {e}")
                # Create empty mapping for failed steps
                mappings.append(StepMapping(
                    step_id=step.id,
                    step=step,
                    matches=[],
                    best_match=None,
                    mapping_confidence=0.0,
                    requires_manual_review=True,
                    suggestions=[f"Error mapping step: {str(e)}"]
                ))
        
        # Post-process mappings to resolve conflicts and optimize
        self._optimize_mappings(mappings)
        
        return mappings
    
    def find_tools_for_step(
        self, 
        step: ParsedStep, 
        max_results: int = 10,
        catalog_filters: Dict[str, str] = None
    ) -> List[ToolMatch]:
        """
        Find potential tool matches for a single step.
        
        Args:
            step: The recipe step to find tools for
            max_results: Maximum number of results to return
            catalog_filters: Optional catalog filtering (catalog_type, catalog_subtype, catalog_name)
            
        Returns:
            List of potential tool matches
        """
        # Get candidate tools using simplified or legacy search
        candidates = self._get_candidate_tools(step, max_results * 2, catalog_filters)
        
        # Score and rank candidates - simplified or legacy approach
        if USE_LEGACY_TOOL_MAPPING:
            # Legacy approach with complex filtering
            tool_matches = []
            filtered_count = 0
            
            for candidate in candidates:
                try:
                    match = self._evaluate_tool_match(step, candidate)
                    logger.info(f"Tool {candidate.get('id')}: similarity={match.similarity_score:.3f}, "
                               f"context={match.context_score:.3f}, compatibility={match.compatibility_score:.3f}, "
                               f"overall={match.overall_confidence:.3f}")
                    
                    if match.overall_confidence > 0.05:  # Very permissive threshold like /v1/complete
                        tool_matches.append(match)
                    else:
                        filtered_count += 1
                        logger.info(f"Filtered out tool {candidate.get('id')} due to low confidence: {match.overall_confidence:.3f}")
                        
                except Exception as e:
                    logger.warning(f"Failed to evaluate tool {candidate.get('id', 'unknown')}: {e}")
            
            logger.info(f"Found {len(tool_matches)} matches above 0.05 threshold, filtered out {filtered_count}")
        else:
            # Simplified approach - no additional filtering, candidates already above 0.4 threshold
            tool_matches = []
            
            for candidate in candidates:
                try:
                    match = self._evaluate_tool_match(step, candidate)
                    tool_matches.append(match)  # No filtering - already filtered by 0.4 threshold in search
                    
                except Exception as e:
                    logger.warning(f"Failed to evaluate tool {candidate.get('id', 'unknown')}: {e}")
            
            logger.info(f"SIMPLIFIED: Processed {len(tool_matches)} candidates (all above 0.4 threshold)")
        
        # Sort by overall confidence and return top matches
        tool_matches.sort(key=lambda x: x.overall_confidence, reverse=True)
        return tool_matches[:max_results]
    
    def _map_single_step(
        self, 
        step: ParsedStep, 
        strategy: MappingStrategy, 
        threshold: float, 
        max_matches: int,
        catalog_filters: Dict[str, str] = None
    ) -> StepMapping:
        """Map a single recipe step to tools."""
        # Find potential tool matches
        matches = self.find_tools_for_step(step, max_matches, catalog_filters)
        
        if USE_LEGACY_TOOL_MAPPING:
            # Legacy approach with additional threshold filtering
            filtered_matches = [m for m in matches if m.overall_confidence >= threshold]
            
            logger.info(f"Step '{step.name}': Found {len(matches)} initial matches, "
                       f"{len(filtered_matches)} passed threshold {threshold}")
            
            if matches and not filtered_matches:
                best_unfiltered = max(matches, key=lambda x: x.overall_confidence)
                logger.info(f"No matches passed threshold {threshold}. Best match was {best_unfiltered.overall_confidence:.3f} "
                           f"for tool {best_unfiltered.tool_id}")
        else:
            # Simplified approach - no additional threshold filtering
            filtered_matches = matches  # Use all matches (already filtered at 0.4 in search)
            logger.info(f"SIMPLIFIED Step '{step.name}': Using all {len(matches)} matches (pre-filtered at 0.4)")
        
        # Determine best match
        best_match = filtered_matches[0] if filtered_matches else None
        
        # Calculate overall mapping confidence
        mapping_confidence = best_match.overall_confidence if best_match else 0.0
        
        # Determine if manual review is needed
        requires_review = (
            mapping_confidence < self.mapping_thresholds["auto_accept"] or
            len(filtered_matches) == 0 or
            (len(filtered_matches) > 1 and 
             filtered_matches[0].overall_confidence - filtered_matches[1].overall_confidence < 0.1)
        )
        
        # Generate suggestions
        suggestions = self._generate_mapping_suggestions(step, matches)
        
        return StepMapping(
            step_id=step.id,
            step=step,
            matches=filtered_matches,
            best_match=best_match,
            mapping_confidence=mapping_confidence,
            requires_manual_review=requires_review,
            suggestions=suggestions
        )
    
    def _get_candidate_tools_legacy(self, step: ParsedStep, max_candidates: int, catalog_filters: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """Get candidate tools using hybrid search approach."""
        # Create search query from step description and context
        search_query = self._build_search_query(step)
        
        # Filter by relevant tool types
        relevant_types = self._get_relevant_tool_types(step)
        
        logger.info(f"Searching for tools with query: '{search_query}', types: {relevant_types}")
        
        # Apply catalog filters if provided
        catalog_type = catalog_filters.get('catalog_type') if catalog_filters else None
        catalog_subtype = catalog_filters.get('catalog_subtype') if catalog_filters else None
        catalog_name = catalog_filters.get('catalog_name') if catalog_filters else None
        
        all_candidates = []
        
        # Phase 1: Semantic search with vector similarity (use higher thresholds like /v1/complete)
        semantic_candidates = []
        for tool_type in relevant_types:
            try:
                results = self.controller.search_query(
                    nl_query=search_query,
                    template_type=tool_type,
                    similarity_threshold=0.6,  # Higher threshold like completion endpoint for better quality
                    limit=max_candidates // len(relevant_types) + 3,
                    catalog_type=catalog_type,
                    catalog_subtype=catalog_subtype,
                    catalog_name=catalog_name
                )
                for result in results:
                    result['search_method'] = 'semantic'
                    result['original_similarity'] = result.get('similarity', 0.0)
                semantic_candidates.extend(results)
            except Exception as e:
                logger.warning(f"Semantic search failed for tool type {tool_type}: {e}")
        
        logger.info(f"Semantic search found {len(semantic_candidates)} candidates")
        all_candidates.extend(semantic_candidates)
        
        # Phase 2: Broad search without template type restrictions (like /v1/complete)
        if len(semantic_candidates) < max_candidates // 2:
            logger.info("Semantic search yielded few results, trying broad search...")
            try:
                broad_results = self.controller.search_query(
                    nl_query=search_query,
                    template_type=None,  # No template type restriction
                    similarity_threshold=0.4,  # Reasonable threshold for broad search
                    limit=max_candidates,
                    catalog_type=catalog_type,
                    catalog_subtype=catalog_subtype,
                    catalog_name=catalog_name
                )
                for result in broad_results:
                    result['search_method'] = 'broad_semantic'
                    result['original_similarity'] = result.get('similarity', 0.0)
                all_candidates.extend(broad_results)
                logger.info(f"Broad search found {len(broad_results)} additional candidates")
            except Exception as e:
                logger.warning(f"Broad search failed: {e}")
        
        # Phase 3: Keyword search fallback
        if len(all_candidates) < max_candidates // 3:
            logger.info("Still few results, trying keyword search...")
            keyword_candidates = self._keyword_search(step, relevant_types, max_candidates, catalog_filters)
            all_candidates.extend(keyword_candidates)
        
        # Phase 4: Ultra-broad catalog search (no catalog filtering)
        if len(all_candidates) < 3:
            logger.info("Very few results, trying ultra-broad search without catalog filters...")
            try:
                ultra_broad_results = self.controller.search_query(
                    nl_query=search_query,
                    template_type=None,
                    similarity_threshold=0.01,  # Extremely low threshold
                    limit=max_candidates * 2,
                    catalog_type=None,  # No catalog filtering
                    catalog_subtype=None,
                    catalog_name=None
                )
                for result in ultra_broad_results:
                    result['search_method'] = 'ultra_broad'
                    result['original_similarity'] = result.get('similarity', 0.0)
                all_candidates.extend(ultra_broad_results)
                logger.info(f"Ultra-broad search found {len(ultra_broad_results)} additional candidates")
            except Exception as e:
                logger.warning(f"Ultra-broad search failed: {e}")
        
        # Remove duplicates and rank by combined score
        seen_ids = set()
        unique_candidates = []
        for candidate in all_candidates:
            if candidate['id'] not in seen_ids:
                seen_ids.add(candidate['id'])
                unique_candidates.append(candidate)
        
        # Sort by relevance score (combination of similarity and search method)
        unique_candidates.sort(key=lambda x: self._calculate_relevance_score(x, step), reverse=True)
        
        logger.info(f"Total unique candidates found: {len(unique_candidates)}")
        return unique_candidates[:max_candidates]
    
    def _keyword_search(self, step: ParsedStep, relevant_types: List[str], max_candidates: int, catalog_filters: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """Perform keyword-based search as fallback."""
        # Build keyword query using entities and action verbs
        keywords = []
        keywords.extend(step.action_verbs[:2])
        keywords.extend(step.entities[:3])
        
        keyword_candidates = []
        
        for tool_type in relevant_types:
            try:
                # Use string search method for keyword matching
                results = self.controller.search_query(
                    nl_query=" ".join(keywords),
                    template_type=tool_type,
                    search_method="string",  # Force string matching
                    similarity_threshold=0.2,  # Lower threshold for keywords
                    limit=max_candidates // len(relevant_types) + 1,
                    catalog_type=catalog_filters.get('catalog_type') if catalog_filters else None,
                    catalog_subtype=catalog_filters.get('catalog_subtype') if catalog_filters else None,
                    catalog_name=catalog_filters.get('catalog_name') if catalog_filters else None
                )
                for result in results:
                    result['search_method'] = 'keyword'
                    result['original_similarity'] = result.get('similarity', 0.0)
                keyword_candidates.extend(results)
            except Exception as e:
                logger.warning(f"Keyword search failed for tool type {tool_type}: {e}")
        
        logger.info(f"Keyword search found {len(keyword_candidates)} candidates")
        return keyword_candidates
    
    def _catalog_search(self, step: ParsedStep, catalog_filters: Dict[str, str], max_candidates: int) -> List[Dict[str, Any]]:
        """Perform broad catalog-based search."""
        catalog_candidates = []
        
        try:
            # Search within the specified catalog without type restrictions
            results = self.controller.search_query(
                nl_query=step.description,
                template_type=None,  # No type restriction
                search_method="string",
                similarity_threshold=0.1,  # Very low threshold
                limit=max_candidates,
                catalog_type=catalog_filters.get('catalog_type'),
                catalog_subtype=catalog_filters.get('catalog_subtype'),
                catalog_name=catalog_filters.get('catalog_name')
            )
            for result in results:
                result['search_method'] = 'catalog'
                result['original_similarity'] = result.get('similarity', 0.0)
            catalog_candidates.extend(results)
        except Exception as e:
            logger.warning(f"Catalog search failed: {e}")
        
        logger.info(f"Catalog search found {len(catalog_candidates)} candidates")
        return catalog_candidates
    
    def _calculate_relevance_score(self, candidate: Dict[str, Any], step: ParsedStep) -> float:
        """Calculate overall relevance score for ranking candidates."""
        base_similarity = candidate.get('similarity', 0.0)
        search_method = candidate.get('search_method', 'semantic')
        
        # Weight different search methods
        method_weights = {
            'semantic': 1.0,    # Highest weight for semantic matches
            'keyword': 0.8,     # Good weight for keyword matches
            'catalog': 0.6      # Lower weight for broad catalog matches
        }
        
        method_weight = method_weights.get(search_method, 0.5)
        
        # Boost score for tool type compatibility
        tool_type = candidate.get('template_type', '')
        relevant_types = self._get_relevant_tool_types(step)
        type_boost = 0.1 if tool_type in relevant_types else 0.0
        
        # Boost score for entity matches in tool name/description
        entity_boost = 0.0
        tool_text = (candidate.get('nl_query', '') + ' ' + candidate.get('template', '')).lower()
        for entity in step.entities:
            if entity.lower() in tool_text:
                entity_boost += 0.05
        
        final_score = (base_similarity * method_weight) + type_boost + min(entity_boost, 0.2)
        return final_score
    
    def _build_search_query(self, step: ParsedStep) -> str:
        """Build optimized search query for finding relevant tools.
        
        FIXED: Now preserves original semantic context like the completion endpoint
        instead of transforming to keywords which destroys meaning.
        """
        # Use the original description to preserve semantic context
        # This matches the successful approach used by the completion endpoint
        original_query = step.description.strip()
        
        # Only do minimal cleanup - remove excessive whitespace but preserve meaning
        cleaned_query = " ".join(original_query.split())
        
        logger.debug(f"Using original semantic query for step '{step.description[:50]}...': '{cleaned_query}'")
        logger.info(f"SEMANTIC SEARCH FIX: Original query preserved instead of keyword transformation")
        
        return cleaned_query
    
    def _get_relevant_tool_types(self, step: ParsedStep) -> List[str]:
        """Get relevant tool types for a recipe step."""
        # Use broad tool types like /v1/complete approach
        # Include all commonly used template types to avoid missing matches
        relevant_types = [
            "function", "api", "mcp_tool", "agent", 
            "sql", "url", "workflow", "script", "cli"
        ]
        
        # Add specific types based on step type
        type_mappings = self.step_type_mappings.get(step.step_type, [])
        relevant_types.extend(type_mappings)
        
        # Add types based on entities and context
        for entity in step.entities:
            if any(ext in entity.lower() for ext in ['.json', '.xml', '.csv']):
                relevant_types.extend(["function", "script"])
            elif 'api' in entity.lower() or 'http' in entity.lower():
                relevant_types.extend(["api", "url"])
            elif any(db in entity.lower() for db in ['database', 'sql', 'query']):
                relevant_types.extend(["sql", "function", "api"])
            elif 'workflow' in entity.lower():
                relevant_types.extend(["workflow", "function"])
        
        # Add context-based types
        step_desc_lower = step.description.lower()
        if any(keyword in step_desc_lower for keyword in ['api', 'endpoint', 'request', 'call']):
            relevant_types.extend(["api", "url"])
        if any(keyword in step_desc_lower for keyword in ['database', 'sql', 'query', 'table']):
            relevant_types.extend(["sql", "function"])
        if any(keyword in step_desc_lower for keyword in ['script', 'command', 'execute']):
            relevant_types.extend(["script", "cli", "function"])
        
        return list(set(relevant_types))
    
    def _evaluate_tool_match_legacy(self, step: ParsedStep, tool_data: Dict[str, Any]) -> ToolMatch:
        """Evaluate how well a tool matches a recipe step."""
        # Extract tool information
        tool_id = tool_data['id']
        tool_name = tool_data['nl_query']
        tool_type = tool_data['template_type']
        
        # Get tool capabilities and ensure it's always a list
        tool_capabilities = tool_data.get('tool_capabilities') or []
        if not isinstance(tool_capabilities, list):
            tool_capabilities = []
        
        # Calculate different scoring components
        similarity_score = tool_data.get('similarity', 0.0)  # Fixed: Use 'similarity' key, not 'similarity_score'
        context_score = self._calculate_context_score(step, tool_data)
        compatibility_score = self._calculate_compatibility_score(step, tool_data)
        
        # Calculate overall confidence using weighted combination
        weights = {
            'similarity': 0.4,
            'context': 0.3,
            'compatibility': 0.3
        }
        
        overall_confidence = (
            similarity_score * weights['similarity'] +
            context_score * weights['context'] +
            compatibility_score * weights['compatibility']
        )
        
        # Generate reasoning explanation
        reasoning = self._generate_match_reasoning(
            step, tool_data, similarity_score, context_score, compatibility_score
        )
        
        return ToolMatch(
            tool_id=tool_id,
            tool_name=tool_name,
            tool_type=tool_type,
            similarity_score=similarity_score,
            context_score=context_score,
            compatibility_score=compatibility_score,
            overall_confidence=overall_confidence,
            reasoning=reasoning,
            tool_capabilities=tool_capabilities,
            tool_data=tool_data
        )
    
    def _calculate_context_score(self, step: ParsedStep, tool_data: Dict[str, Any]) -> float:
        """Calculate contextual compatibility score between step and tool."""
        score = 0.5  # Base score
        
        tool_type = tool_data['template_type']
        
        # Step type to tool type compatibility
        compatible_types = self.step_type_mappings.get(step.step_type, [])
        if tool_type in compatible_types:
            score += 0.3
        
        # Action verb compatibility
        tool_capabilities = tool_data.get('tool_capabilities') or []
        # Ensure tool_capabilities is always a list
        if not isinstance(tool_capabilities, list):
            tool_capabilities = []
            
        for verb in step.action_verbs:
            if any(verb in cap.lower() for cap in tool_capabilities):
                score += 0.05
        
        # Entity compatibility
        tool_description = tool_data.get('template', '').lower()
        for entity in step.entities:
            if entity.lower() in tool_description:
                score += 0.05
        
        return min(1.0, score)
    
    def _calculate_compatibility_score(self, step: ParsedStep, tool_data: Dict[str, Any]) -> float:
        """Calculate technical compatibility score."""
        score = 0.5  # Base score
        
        # Health status consideration
        health_status = tool_data.get('health_status', 'unknown')
        health_scores = {
            'healthy': 0.3,
            'degraded': 0.1,
            'unhealthy': -0.2,
            'unknown': 0.0
        }
        score += health_scores.get(health_status, 0.0)
        
        # Usage count as popularity indicator
        usage_count = tool_data.get('usage_count', 0)
        if usage_count > 10:
            score += 0.1
        elif usage_count > 50:
            score += 0.2
        
        # Template complexity compatibility
        is_template = tool_data.get('is_template', False)
        if is_template and step.confidence > 0.7:
            score += 0.1  # High confidence steps work well with templates
        
        return min(1.0, max(0.0, score))
    
    def _generate_match_reasoning(
        self, 
        step: ParsedStep, 
        tool_data: Dict[str, Any], 
        sim_score: float, 
        ctx_score: float, 
        comp_score: float
    ) -> str:
        """Generate human-readable reasoning for the match."""
        reasons = []
        
        # Similarity reasoning
        if sim_score > 0.8:
            reasons.append("High semantic similarity")
        elif sim_score > 0.6:
            reasons.append("Good semantic match")
        elif sim_score > 0.4:
            reasons.append("Moderate semantic similarity")
        
        # Context reasoning
        if ctx_score > 0.7:
            reasons.append("Strong contextual compatibility")
        else:
            # Safely handle tool_capabilities that might be None
            tool_capabilities = tool_data.get('tool_capabilities') or []
            if not isinstance(tool_capabilities, list):
                tool_capabilities = []
            
            if any(verb in cap for cap in tool_capabilities for verb in step.action_verbs if isinstance(cap, str)):
                reasons.append("Matching capabilities found")
        
        # Compatibility reasoning
        health = tool_data.get('health_status', 'unknown')
        if health == 'healthy':
            reasons.append("Tool is healthy and reliable")
        elif health == 'degraded':
            reasons.append("Tool has some issues")
        
        usage = tool_data.get('usage_count', 0)
        if usage > 50:
            reasons.append("Popular, well-tested tool")
        
        return "; ".join(reasons) if reasons else "Basic compatibility match"
    
    def _generate_mapping_suggestions(self, step: ParsedStep, matches: List[ToolMatch]) -> List[str]:
        """Generate helpful suggestions for step mapping."""
        suggestions = []
        
        if not matches:
            suggestions.append("No compatible tools found. Consider creating a custom tool for this step.")
            suggestions.append(f"Step type '{step.step_type.value}' might need specialized tooling.")
        elif len(matches) == 1:
            if matches[0].overall_confidence < 0.5:
                suggestions.append("Low confidence match. Manual review recommended.")
            else:
                suggestions.append("Single good match found. Consider validating before use.")
        else:
            # Multiple matches
            top_match = matches[0]
            if len([m for m in matches if m.overall_confidence > 0.7]) > 1:
                suggestions.append("Multiple high-quality matches available. Choose based on specific requirements.")
            
            suggestions.append(f"Top match: {top_match.tool_name} ({top_match.overall_confidence:.2f} confidence)")
        
        # Add specific suggestions based on step characteristics
        if step.step_type == StepType.INTEGRATION and not any(m.tool_type == 'api' for m in matches):
            suggestions.append("Consider using an API tool for this integration step.")
        elif step.step_type == StepType.TRANSFORM and not any(m.tool_type == 'function' for m in matches):
            suggestions.append("Data transformation typically works best with function tools.")
        
        return suggestions
    
    def _optimize_mappings(self, mappings: List[StepMapping]) -> None:
        """Optimize mappings to avoid conflicts and improve overall recipe quality."""
        # Check for tool conflicts (same tool used multiple times)
        tool_usage = {}
        
        for mapping in mappings:
            if mapping.best_match:
                tool_id = mapping.best_match.tool_id
                if tool_id in tool_usage:
                    tool_usage[tool_id].append(mapping)
                else:
                    tool_usage[tool_id] = [mapping]
        
        # Resolve conflicts by reassigning lower-confidence mappings
        for tool_id, conflicting_mappings in tool_usage.items():
            if len(conflicting_mappings) > 1:
                # Sort by confidence, keep highest confidence mapping
                conflicting_mappings.sort(key=lambda x: x.mapping_confidence, reverse=True)
                
                # Reassign lower confidence mappings to alternative matches
                for mapping in conflicting_mappings[1:]:
                    alternative_matches = [m for m in mapping.matches if m.tool_id != tool_id]
                    if alternative_matches:
                        mapping.best_match = alternative_matches[0]
                        mapping.mapping_confidence = alternative_matches[0].overall_confidence
                        mapping.suggestions.append("Reassigned to avoid tool conflict")
                    else:
                        mapping.best_match = None
                        mapping.requires_manual_review = True
                        mapping.suggestions.append("No alternative matches available due to conflict")
    
    def _get_mapping_thresholds(self) -> Dict[str, float]:
        """Get confidence thresholds for automatic mapping."""
        return {
            'auto_accept': 0.8,    # Automatically accept matches above this threshold
            'manual_review': 0.5,  # Require manual review below this threshold
            'reject': 0.2          # Automatically reject matches below this threshold
        }
    
    def _get_step_type_tool_mappings(self) -> Dict[StepType, List[str]]:
        """Get preferred tool types for each step type."""
        return {
            StepType.ACTION: ["function", "mcp_tool", "agent"],
            StepType.CONDITION: ["function", "agent"],
            StepType.LOOP: ["function", "agent"],
            StepType.TRANSFORM: ["function", "mcp_tool"],
            StepType.VALIDATION: ["function", "agent"],
            StepType.INTEGRATION: ["api", "mcp_tool", "agent"],
            StepType.UNKNOWN: ["function", "mcp_tool", "agent", "api"]
        }
    
    # ========================
    # SIMPLIFIED TOOL MAPPING METHODS
    # ========================
    
    def _get_candidate_tools(self, step: ParsedStep, max_candidates: int, catalog_filters: Dict[str, str] = None) -> List[Dict[str, Any]]:
        """
        Simplified tool candidate search using direct similarity search with 0.4+ threshold.
        
        This replaces the complex multi-phase search with a single, focused similarity search.
        """
        if USE_LEGACY_TOOL_MAPPING:
            return self._get_candidate_tools_legacy(step, max_candidates, catalog_filters)
        
        # Build search query from step description
        search_query = step.description
        logger.info(f"SIMPLIFIED SEARCH: '{search_query}' (threshold: 0.4)")
        
        # Apply catalog filters if provided
        catalog_type = catalog_filters.get('catalog_type') if catalog_filters else None
        catalog_subtype = catalog_filters.get('catalog_subtype') if catalog_filters else None
        catalog_name = catalog_filters.get('catalog_name') if catalog_filters else None
        
        try:
            # Single similarity search across all tool types with 0.4 threshold
            results = self.controller.search_query(
                nl_query=search_query,
                template_type=None,  # Search all tool types
                similarity_threshold=0.4,  # Primary threshold for quality results
                limit=max(max_candidates, 50),  # Ensure we get more results than the artificial 10 limit
                catalog_type=catalog_type,
                catalog_subtype=catalog_subtype,
                catalog_name=catalog_name
            )
            
            # Add search metadata to results
            for result in results:
                result['search_method'] = 'simplified_similarity'
                result['original_similarity'] = result.get('similarity', 0.0)
            
            logger.info(f"SIMPLIFIED SEARCH: Found {len(results)} candidates above 0.4 threshold")
            return results
            
        except Exception as e:
            logger.error(f"Simplified search failed: {e}")
            return []
    
    def _evaluate_tool_match(self, step: ParsedStep, tool_data: Dict[str, Any]) -> ToolMatch:
        """
        Simplified tool match evaluation focusing on similarity score as primary factor.
        
        This replaces complex scoring with a straightforward similarity-based approach.
        """
        if USE_LEGACY_TOOL_MAPPING:
            return self._evaluate_tool_match_legacy(step, tool_data)
        
        # Get similarity score (using correct key)
        similarity_score = tool_data.get('similarity', 0.0)
        
        # Simple confidence calculation: use similarity score directly if above 0.4
        overall_confidence = max(similarity_score, 0.4) if similarity_score >= 0.4 else similarity_score
        
        # Create tool match with simplified scoring
        tool_match = ToolMatch(
            tool_id=tool_data.get('id', 0),
            tool_name=tool_data.get('nl_query', f"Tool {tool_data.get('id', 'Unknown')}"),
            tool_type=tool_data.get('template_type', 'unknown'),
            similarity_score=similarity_score,
            context_score=0.5,  # Simplified: fixed moderate score
            compatibility_score=0.5,  # Simplified: fixed moderate score  
            overall_confidence=overall_confidence,
            reasoning=f"Similarity match: {similarity_score:.3f} (simplified scoring)",
            tool_capabilities=[],  # Could be enhanced later if needed
            tool_data=tool_data
        )
        
        return tool_match