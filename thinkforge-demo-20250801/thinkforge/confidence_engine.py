"""
Confidence Scoring Engine for ThinkForge Recipe Mapping

This module provides comprehensive confidence scoring for recipe step analysis,
tool matching, and mapping validation with detailed explanations.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from datetime import datetime, timedelta

from .recipe_step_analyzer import ParsedStep, StepType

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence levels for various assessments."""
    VERY_HIGH = "very_high"  # 0.9-1.0
    HIGH = "high"            # 0.7-0.89
    MEDIUM = "medium"        # 0.5-0.69
    LOW = "low"              # 0.3-0.49
    VERY_LOW = "very_low"    # 0.0-0.29


@dataclass
class ConfidenceScore:
    """Detailed confidence score with breakdown and reasoning."""
    overall_score: float
    level: ConfidenceLevel
    components: Dict[str, float]
    reasoning: List[str]
    recommendations: List[str]
    factors: Dict[str, Any]


@dataclass
class MappingConfidence:
    """Confidence assessment for step-to-tool mapping."""
    step_confidence: ConfidenceScore
    tool_compatibility: ConfidenceScore
    semantic_similarity: ConfidenceScore
    contextual_match: ConfidenceScore
    overall_mapping: ConfidenceScore
    auto_accept: bool
    requires_review: bool


class ConfidenceEngine:
    """
    Comprehensive confidence scoring engine for recipe mapping operations.
    
    Provides detailed confidence assessments with explanations and recommendations
    for various aspects of the recipe mapping process.
    """
    
    def __init__(self):
        """Initialize the confidence scoring engine."""
        self.thresholds = self._get_confidence_thresholds()
        self.weights = self._get_scoring_weights()
        self.historical_performance = {}  # Could be loaded from database
        
    def assess_step_parsing_confidence(self, step: ParsedStep) -> ConfidenceScore:
        """
        Assess confidence in recipe step parsing quality.
        
        Args:
            step: The parsed recipe step to assess
            
        Returns:
            Detailed confidence score for the step parsing
        """
        components = {}
        reasoning = []
        recommendations = []
        factors = {}
        
        # 1. Text clarity and structure
        text_score = self._assess_text_clarity(step.raw_text)
        components['text_clarity'] = text_score
        factors['text_length'] = len(step.raw_text.split())
        
        if text_score > 0.8:
            reasoning.append("Step text is clear and well-structured")
        elif text_score > 0.6:
            reasoning.append("Step text is reasonably clear")
        else:
            reasoning.append("Step text lacks clarity or structure")
            recommendations.append("Consider rephrasing the step for better clarity")
        
        # 2. Action verb identification
        action_score = self._assess_action_verbs(step)
        components['action_identification'] = action_score
        factors['action_verb_count'] = len(step.action_verbs)
        
        if action_score > 0.7:
            reasoning.append(f"Clear action verbs identified: {', '.join(step.action_verbs[:3])}")
        elif action_score > 0.4:
            reasoning.append("Some action verbs identified")
        else:
            reasoning.append("No clear action verbs identified")
            recommendations.append("Add clear action verbs to improve step clarity")
        
        # 3. Entity extraction quality
        entity_score = self._assess_entity_extraction(step)
        components['entity_extraction'] = entity_score
        factors['entity_count'] = len(step.entities)
        
        if entity_score > 0.6:
            reasoning.append(f"Good entity extraction: {len(step.entities)} entities found")
        elif entity_score > 0.3:
            reasoning.append("Some entities identified")
        else:
            reasoning.append("Limited entity extraction")
            recommendations.append("Include more specific entities or parameters")
        
        # 4. Step type classification confidence
        type_score = self._assess_step_type_classification(step)
        components['type_classification'] = type_score
        factors['step_type'] = step.step_type.value
        
        if type_score > 0.8:
            reasoning.append(f"Step clearly classified as {step.step_type.value}")
        elif type_score > 0.5:
            reasoning.append(f"Step tentatively classified as {step.step_type.value}")
        else:
            reasoning.append("Step type classification uncertain")
            recommendations.append("Provide more context to improve type classification")
        
        # 5. Parameter extraction
        param_score = self._assess_parameter_extraction(step)
        components['parameter_extraction'] = param_score
        factors['parameter_count'] = len(step.parameters)
        
        if param_score > 0.5:
            reasoning.append(f"Parameters extracted: {list(step.parameters.keys())[:3]}")
        
        # Calculate overall score
        overall_score = np.average(
            list(components.values()),
            weights=[0.25, 0.25, 0.2, 0.2, 0.1]
        )
        
        level = self._score_to_level(overall_score)
        
        # Add level-specific recommendations
        if level in [ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]:
            recommendations.append("Consider breaking this step into smaller, more specific steps")
            recommendations.append("Add more descriptive details about the required action")
        
        return ConfidenceScore(
            overall_score=overall_score,
            level=level,
            components=components,
            reasoning=reasoning,
            recommendations=recommendations,
            factors=factors
        )
    
    def assess_tool_compatibility(self, step: ParsedStep, tool_data: Dict[str, Any]) -> ConfidenceScore:
        """
        Assess confidence in tool compatibility with a recipe step.
        
        Args:
            step: The recipe step
            tool_data: Tool information from the database
            
        Returns:
            Confidence score for tool compatibility
        """
        components = {}
        reasoning = []
        recommendations = []
        factors = {}
        
        tool_name = tool_data.get('nl_query', 'Unknown')
        tool_type = tool_data.get('template_type', 'unknown')
        
        # 1. Tool type compatibility
        type_score = self._assess_tool_type_compatibility(step, tool_type)
        components['type_compatibility'] = type_score
        factors['tool_type'] = tool_type
        factors['step_type'] = step.step_type.value
        
        if type_score > 0.8:
            reasoning.append(f"{tool_type} tool is excellent for {step.step_type.value} steps")
        elif type_score > 0.5:
            reasoning.append(f"{tool_type} tool is suitable for {step.step_type.value} steps")
        else:
            reasoning.append(f"{tool_type} tool may not be ideal for {step.step_type.value} steps")
            recommendations.append(f"Consider looking for {self._get_preferred_tool_types(step.step_type)} tools")
        
        # 2. Capability matching
        capability_score = self._assess_capability_matching(step, tool_data)
        components['capability_match'] = capability_score
        tool_capabilities = tool_data.get('tool_capabilities', [])
        factors['tool_capabilities'] = tool_capabilities
        
        if capability_score > 0.7:
            reasoning.append("Tool capabilities align well with step requirements")
        elif capability_score > 0.4:
            reasoning.append("Some tool capabilities match step requirements")
        else:
            reasoning.append("Limited capability match")
            recommendations.append("Verify tool capabilities match step requirements")
        
        # 3. Tool health and reliability
        health_score = self._assess_tool_health(tool_data)
        components['tool_health'] = health_score
        health_status = tool_data.get('health_status', 'unknown')
        factors['health_status'] = health_status
        
        if health_score > 0.8:
            reasoning.append("Tool is healthy and reliable")
        elif health_score > 0.5:
            reasoning.append("Tool health is acceptable")
        else:
            reasoning.append("Tool may have reliability issues")
            recommendations.append("Consider testing tool before use or finding alternatives")
        
        # 4. Usage history and popularity
        usage_score = self._assess_tool_usage_history(tool_data)
        components['usage_history'] = usage_score
        usage_count = tool_data.get('usage_count', 0)
        factors['usage_count'] = usage_count
        
        if usage_score > 0.7:
            reasoning.append("Tool is well-tested and popular")
        elif usage_score > 0.4:
            reasoning.append("Tool has moderate usage")
        else:
            reasoning.append("Tool has limited usage history")
            recommendations.append("Consider testing thoroughly before production use")
        
        # 5. Template complexity alignment
        complexity_score = self._assess_template_complexity_alignment(step, tool_data)
        components['complexity_alignment'] = complexity_score
        
        # Calculate overall score
        overall_score = np.average(
            list(components.values()),
            weights=[0.3, 0.25, 0.2, 0.15, 0.1]
        )
        
        level = self._score_to_level(overall_score)
        
        return ConfidenceScore(
            overall_score=overall_score,
            level=level,
            components=components,
            reasoning=reasoning,
            recommendations=recommendations,
            factors=factors
        )
    
    def assess_semantic_similarity(self, step: ParsedStep, tool_data: Dict[str, Any], similarity_score: float) -> ConfidenceScore:
        """
        Assess confidence in semantic similarity between step and tool.
        
        Args:
            step: The recipe step
            tool_data: Tool information
            similarity_score: Raw similarity score from vector search
            
        Returns:
            Confidence score for semantic similarity
        """
        components = {}
        reasoning = []
        recommendations = []
        factors = {}
        
        # 1. Raw similarity score assessment
        raw_score = min(1.0, max(0.0, similarity_score))
        components['raw_similarity'] = raw_score
        factors['similarity_score'] = similarity_score
        
        if raw_score > 0.8:
            reasoning.append("Very high semantic similarity")
        elif raw_score > 0.6:
            reasoning.append("Good semantic similarity")
        elif raw_score > 0.4:
            reasoning.append("Moderate semantic similarity")
        else:
            reasoning.append("Low semantic similarity")
            recommendations.append("Consider more specific search terms or alternative tools")
        
        # 2. Context relevance
        context_score = self._assess_semantic_context_relevance(step, tool_data)
        components['context_relevance'] = context_score
        
        if context_score > 0.7:
            reasoning.append("Tool context aligns well with step context")
        elif context_score > 0.4:
            reasoning.append("Some contextual alignment")
        else:
            reasoning.append("Limited contextual alignment")
        
        # 3. Keyword overlap
        keyword_score = self._assess_keyword_overlap(step, tool_data)
        components['keyword_overlap'] = keyword_score
        
        if keyword_score > 0.6:
            reasoning.append("Good keyword overlap between step and tool")
        
        # 4. Embedding quality assessment
        embedding_score = self._assess_embedding_quality(step, tool_data)
        components['embedding_quality'] = embedding_score
        
        # Calculate overall score
        overall_score = np.average(
            list(components.values()),
            weights=[0.4, 0.3, 0.2, 0.1]
        )
        
        level = self._score_to_level(overall_score)
        
        # Add similarity-specific recommendations
        if level == ConfidenceLevel.VERY_LOW:
            recommendations.append("Similarity is very low - consider alternative search strategies")
        elif level == ConfidenceLevel.LOW:
            recommendations.append("Low similarity - manual verification strongly recommended")
        
        return ConfidenceScore(
            overall_score=overall_score,
            level=level,
            components=components,
            reasoning=reasoning,
            recommendations=recommendations,
            factors=factors
        )
    
    def assess_overall_mapping_confidence(
        self, 
        step_confidence: ConfidenceScore,
        tool_compatibility: ConfidenceScore,
        semantic_similarity: ConfidenceScore
    ) -> MappingConfidence:
        """
        Assess overall confidence in a step-to-tool mapping.
        
        Args:
            step_confidence: Confidence in step parsing
            tool_compatibility: Confidence in tool compatibility
            semantic_similarity: Confidence in semantic similarity
            
        Returns:
            Comprehensive mapping confidence assessment
        """
        # Calculate contextual match as combination of compatibility and parsing
        contextual_components = {
            'step_clarity': step_confidence.overall_score * 0.4,
            'tool_suitability': tool_compatibility.overall_score * 0.6
        }
        
        contextual_score = sum(contextual_components.values())
        contextual_match = ConfidenceScore(
            overall_score=contextual_score,
            level=self._score_to_level(contextual_score),
            components=contextual_components,
            reasoning=["Combined assessment of step clarity and tool suitability"],
            recommendations=[],
            factors={}
        )
        
        # Calculate overall mapping confidence
        mapping_components = {
            'step_parsing': step_confidence.overall_score,
            'tool_compatibility': tool_compatibility.overall_score,
            'semantic_similarity': semantic_similarity.overall_score,
            'contextual_match': contextual_score
        }
        
        # Weighted average for overall score
        overall_score = np.average(
            [step_confidence.overall_score, tool_compatibility.overall_score, semantic_similarity.overall_score],
            weights=[0.2, 0.4, 0.4]
        )
        
        overall_reasoning = []
        overall_recommendations = []
        
        # Combine reasoning from all components
        overall_reasoning.extend(step_confidence.reasoning[:2])
        overall_reasoning.extend(tool_compatibility.reasoning[:2])
        overall_reasoning.extend(semantic_similarity.reasoning[:2])
        
        # Combine recommendations
        overall_recommendations.extend(step_confidence.recommendations[:1])
        overall_recommendations.extend(tool_compatibility.recommendations[:1])
        overall_recommendations.extend(semantic_similarity.recommendations[:1])
        
        overall_mapping = ConfidenceScore(
            overall_score=overall_score,
            level=self._score_to_level(overall_score),
            components=mapping_components,
            reasoning=overall_reasoning,
            recommendations=list(set(overall_recommendations)),  # Remove duplicates
            factors={}
        )
        
        # Determine auto-accept and review requirements
        auto_accept = overall_score >= self.thresholds['auto_accept']
        requires_review = overall_score < self.thresholds['manual_review']
        
        return MappingConfidence(
            step_confidence=step_confidence,
            tool_compatibility=tool_compatibility,
            semantic_similarity=semantic_similarity,
            contextual_match=contextual_match,
            overall_mapping=overall_mapping,
            auto_accept=auto_accept,
            requires_review=requires_review
        )
    
    # Helper methods for specific assessments
    
    def _assess_text_clarity(self, text: str) -> float:
        """Assess the clarity and structure of text."""
        score = 0.5  # Base score
        
        words = text.split()
        word_count = len(words)
        
        # Optimal length bonus
        if 5 <= word_count <= 30:
            score += 0.3
        elif word_count < 5:
            score -= 0.2
        elif word_count > 50:
            score -= 0.1
        
        # Sentence structure
        if text.count('.') > 0 or text.count('!') > 0 or text.count('?') > 0:
            score += 0.1
        
        # Capitalization
        if text[0].isupper():
            score += 0.05
        
        # No excessive punctuation
        if text.count('...') == 0 and text.count('!!') == 0:
            score += 0.05
        
        return min(1.0, max(0.0, score))
    
    def _assess_action_verbs(self, step: ParsedStep) -> float:
        """Assess quality of action verb identification."""
        if not step.action_verbs:
            return 0.0
        
        # Base score for having action verbs
        score = 0.4 + (len(step.action_verbs) * 0.15)
        
        # Quality bonus for specific action verbs
        high_quality_verbs = {'create', 'process', 'transform', 'validate', 'send', 'receive', 'analyze', 'execute'}
        quality_verbs = [v for v in step.action_verbs if v in high_quality_verbs]
        score += len(quality_verbs) * 0.1
        
        return min(1.0, score)
    
    def _assess_entity_extraction(self, step: ParsedStep) -> float:
        """Assess quality of entity extraction."""
        if not step.entities:
            return 0.2  # Base score even without entities
        
        score = 0.3 + (len(step.entities) * 0.1)
        
        # Quality bonuses for different entity types
        for entity in step.entities:
            if '.' in entity and len(entity) > 3:  # Likely filename
                score += 0.1
            elif '_' in entity or entity.isupper():  # Likely variable/constant
                score += 0.05
            elif len(entity) > 1:  # Valid entity
                score += 0.02
        
        return min(1.0, score)
    
    def _assess_step_type_classification(self, step: ParsedStep) -> float:
        """Assess confidence in step type classification."""
        if step.step_type == StepType.UNKNOWN:
            return 0.1
        
        # Base confidence varies by type
        type_confidence = {
            StepType.ACTION: 0.8,
            StepType.CONDITION: 0.7,
            StepType.LOOP: 0.7,
            StepType.TRANSFORM: 0.8,
            StepType.VALIDATION: 0.7,
            StepType.INTEGRATION: 0.8
        }
        
        base_score = type_confidence.get(step.step_type, 0.5)
        
        # Boost based on supporting evidence
        text_lower = step.description.lower()
        type_keywords = {
            StepType.ACTION: ['create', 'delete', 'update', 'execute', 'run'],
            StepType.CONDITION: ['if', 'when', 'check', 'verify', 'validate'],
            StepType.LOOP: ['for', 'while', 'repeat', 'iterate', 'each'],
            StepType.TRANSFORM: ['convert', 'transform', 'process', 'format', 'parse'],
            StepType.VALIDATION: ['validate', 'verify', 'check', 'ensure', 'confirm'],
            StepType.INTEGRATION: ['api', 'service', 'call', 'request', 'endpoint']
        }
        
        keywords = type_keywords.get(step.step_type, [])
        keyword_matches = sum(1 for keyword in keywords if keyword in text_lower)
        
        if keyword_matches > 0:
            base_score += keyword_matches * 0.05
        
        return min(1.0, base_score)
    
    def _assess_parameter_extraction(self, step: ParsedStep) -> float:
        """Assess quality of parameter extraction."""
        if not step.parameters:
            return 0.3  # Base score
        
        score = 0.5 + (len(step.parameters) * 0.1)
        
        # Quality bonuses
        for key, value in step.parameters.items():
            if isinstance(value, (int, float)):  # Numeric parameters
                score += 0.05
            elif isinstance(value, str) and len(value) > 0:
                score += 0.03
        
        return min(1.0, score)
    
    def _assess_tool_type_compatibility(self, step: ParsedStep, tool_type: str) -> float:
        """Assess how compatible a tool type is with a step type."""
        compatibility_matrix = {
            StepType.ACTION: {
                'function': 0.9, 'mcp_tool': 0.8, 'agent': 0.7, 'api': 0.6, 'workflow': 0.5
            },
            StepType.CONDITION: {
                'function': 0.9, 'agent': 0.8, 'mcp_tool': 0.6, 'api': 0.4, 'workflow': 0.3
            },
            StepType.LOOP: {
                'function': 0.9, 'agent': 0.7, 'workflow': 0.6, 'mcp_tool': 0.5, 'api': 0.3
            },
            StepType.TRANSFORM: {
                'function': 0.95, 'mcp_tool': 0.8, 'agent': 0.6, 'api': 0.5, 'workflow': 0.4
            },
            StepType.VALIDATION: {
                'function': 0.9, 'agent': 0.8, 'mcp_tool': 0.7, 'api': 0.5, 'workflow': 0.4
            },
            StepType.INTEGRATION: {
                'api': 0.95, 'mcp_tool': 0.9, 'agent': 0.7, 'function': 0.6, 'workflow': 0.5
            },
            StepType.UNKNOWN: {
                'function': 0.5, 'mcp_tool': 0.5, 'agent': 0.5, 'api': 0.5, 'workflow': 0.5
            }
        }
        
        step_compatibilities = compatibility_matrix.get(step.step_type, {})
        return step_compatibilities.get(tool_type, 0.3)
    
    def _assess_capability_matching(self, step: ParsedStep, tool_data: Dict[str, Any]) -> float:
        """Assess how well tool capabilities match step requirements."""
        tool_capabilities = tool_data.get('tool_capabilities', [])
        if not tool_capabilities:
            return 0.4  # Neutral score if no capabilities listed
        
        score = 0.3  # Base score
        
        # Check for action verb matches in capabilities
        for verb in step.action_verbs:
            for capability in tool_capabilities:
                if verb.lower() in capability.lower():
                    score += 0.15
        
        # Check for entity matches in capabilities
        for entity in step.entities:
            for capability in tool_capabilities:
                if entity.lower() in capability.lower():
                    score += 0.1
        
        # Check for step type related capabilities
        step_type_keywords = {
            StepType.TRANSFORM: ['transform', 'convert', 'process', 'format'],
            StepType.VALIDATION: ['validate', 'verify', 'check'],
            StepType.INTEGRATION: ['api', 'service', 'integration', 'connect'],
        }
        
        keywords = step_type_keywords.get(step.step_type, [])
        for keyword in keywords:
            for capability in tool_capabilities:
                if keyword in capability.lower():
                    score += 0.1
        
        return min(1.0, score)
    
    def _assess_tool_health(self, tool_data: Dict[str, Any]) -> float:
        """Assess tool health and reliability."""
        health_status = tool_data.get('health_status', 'unknown')
        
        health_scores = {
            'healthy': 1.0,
            'degraded': 0.6,
            'unhealthy': 0.2,
            'unknown': 0.5
        }
        
        base_score = health_scores.get(health_status, 0.5)
        
        # Adjust based on last tested time
        last_tested = tool_data.get('last_tested')
        if last_tested:
            try:
                last_test_date = datetime.fromisoformat(last_tested.replace('Z', '+00:00'))
                days_ago = (datetime.now() - last_test_date.replace(tzinfo=None)).days
                
                if days_ago <= 7:
                    base_score += 0.1  # Recently tested bonus
                elif days_ago > 30:
                    base_score -= 0.1  # Long time since test penalty
            except:
                pass  # Ignore date parsing errors
        
        return min(1.0, max(0.0, base_score))
    
    def _assess_tool_usage_history(self, tool_data: Dict[str, Any]) -> float:
        """Assess tool based on usage history."""
        usage_count = tool_data.get('usage_count', 0)
        
        if usage_count == 0:
            return 0.3
        elif usage_count < 5:
            return 0.4
        elif usage_count < 20:
            return 0.6
        elif usage_count < 100:
            return 0.8
        else:
            return 1.0
    
    def _assess_template_complexity_alignment(self, step: ParsedStep, tool_data: Dict[str, Any]) -> float:
        """Assess if tool complexity aligns with step complexity."""
        is_template = tool_data.get('is_template', False)
        template_str = tool_data.get('template', '')
        
        # Estimate tool complexity
        tool_complexity = 0.5
        if len(template_str) > 500:
            tool_complexity += 0.2
        if template_str.count('{') > 3:  # JSON complexity
            tool_complexity += 0.1
        if is_template:
            tool_complexity += 0.1
        
        # Estimate step complexity
        step_complexity = step.confidence
        if len(step.parameters) > 2:
            step_complexity += 0.1
        if len(step.entities) > 3:
            step_complexity += 0.1
        
        # Good alignment if complexities are similar
        complexity_diff = abs(tool_complexity - step_complexity)
        alignment_score = max(0.3, 1.0 - complexity_diff)
        
        return alignment_score
    
    def _assess_semantic_context_relevance(self, step: ParsedStep, tool_data: Dict[str, Any]) -> float:
        """Assess contextual relevance beyond just similarity score."""
        score = 0.5  # Base score
        
        tool_description = tool_data.get('template', '').lower()
        step_text = step.description.lower()
        
        # Check for domain-specific terms
        common_domains = ['database', 'api', 'file', 'data', 'web', 'email', 'report']
        for domain in common_domains:
            if domain in step_text and domain in tool_description:
                score += 0.1
        
        # Check for technical terms
        tech_terms = ['json', 'xml', 'csv', 'sql', 'http', 'rest', 'graphql']
        for term in tech_terms:
            if term in step_text and term in tool_description:
                score += 0.05
        
        return min(1.0, score)
    
    def _assess_keyword_overlap(self, step: ParsedStep, tool_data: Dict[str, Any]) -> float:
        """Assess keyword overlap between step and tool."""
        step_words = set(step.description.lower().split())
        tool_words = set(tool_data.get('nl_query', '').lower().split())
        
        if not step_words or not tool_words:
            return 0.3
        
        overlap = len(step_words.intersection(tool_words))
        union = len(step_words.union(tool_words))
        
        if union == 0:
            return 0.3
        
        return overlap / union
    
    def _assess_embedding_quality(self, step: ParsedStep, tool_data: Dict[str, Any]) -> float:
        """Assess quality of embeddings (placeholder for future enhancement)."""
        # This could analyze embedding vector quality, but for now return neutral score
        return 0.7
    
    def _get_preferred_tool_types(self, step_type: StepType) -> str:
        """Get preferred tool types for a step type."""
        preferences = {
            StepType.ACTION: "function or mcp_tool",
            StepType.CONDITION: "function or agent",
            StepType.LOOP: "function or agent",
            StepType.TRANSFORM: "function",
            StepType.VALIDATION: "function or agent",
            StepType.INTEGRATION: "api or mcp_tool",
            StepType.UNKNOWN: "function"
        }
        return preferences.get(step_type, "function")
    
    def _score_to_level(self, score: float) -> ConfidenceLevel:
        """Convert numeric score to confidence level."""
        if score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 0.7:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def _get_confidence_thresholds(self) -> Dict[str, float]:
        """Get confidence thresholds for decision making."""
        return {
            'auto_accept': 0.8,     # Automatically accept mappings above this
            'manual_review': 0.5,   # Require manual review below this
            'auto_reject': 0.2      # Automatically reject below this
        }
    
    def _get_scoring_weights(self) -> Dict[str, Dict[str, float]]:
        """Get weights for different scoring components."""
        return {
            'step_parsing': {
                'text_clarity': 0.25,
                'action_identification': 0.25,
                'entity_extraction': 0.2,
                'type_classification': 0.2,
                'parameter_extraction': 0.1
            },
            'tool_compatibility': {
                'type_compatibility': 0.3,
                'capability_match': 0.25,
                'tool_health': 0.2,
                'usage_history': 0.15,
                'complexity_alignment': 0.1
            },
            'overall_mapping': {
                'step_parsing': 0.2,
                'tool_compatibility': 0.4,
                'semantic_similarity': 0.4
            }
        }