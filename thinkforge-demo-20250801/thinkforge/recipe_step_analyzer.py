"""
Recipe Step Analyzer for ThinkForge

This module provides intelligent parsing of natural language recipes into structured steps
that can be mapped to executable tools and components. It handles various recipe formats
and extracts actionable steps with context and dependencies.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)


class StepType(str, Enum):
    """Types of recipe steps that can be identified."""
    ACTION = "action"           # Direct action to perform
    CONDITION = "condition"     # Conditional logic
    LOOP = "loop"              # Iterative operations
    TRANSFORM = "transform"     # Data transformation
    VALIDATION = "validation"   # Data validation/checking
    INTEGRATION = "integration" # API/service integration
    UNKNOWN = "unknown"        # Unclassified step


@dataclass
class ParsedStep:
    """Represents a parsed recipe step with metadata."""
    id: str
    name: str
    description: str
    step_type: StepType
    order: int
    action_verbs: List[str]
    entities: List[str]
    parameters: Dict[str, Any]
    dependencies: List[str]
    confidence: float
    raw_text: str


@dataclass
class RecipeAnalysis:
    """Complete analysis of a natural language recipe."""
    recipe_name: str
    description: str
    steps: List[ParsedStep]
    total_steps: int
    complexity_score: float
    estimated_duration: Optional[int]  # minutes
    required_capabilities: List[str]
    recipe_type: str


class RecipeStepAnalyzer:
    """
    Intelligent analyzer for parsing natural language recipes into structured steps.
    
    Uses NLP techniques and pattern recognition to extract actionable steps from
    free-form recipe descriptions, preparing them for tool mapping.
    """
    
    def __init__(self):
        """Initialize the recipe step analyzer."""
        self.step_patterns = self._compile_step_patterns()
        self.action_verbs = self._load_action_verbs()
        self.entity_patterns = self._compile_entity_patterns()
        self.dependency_patterns = self._compile_dependency_patterns()
    
    def analyze_recipe(self, recipe_text: str, recipe_name: str = "") -> RecipeAnalysis:
        """
        Analyze a natural language recipe and extract structured steps.
        
        Args:
            recipe_text: The raw recipe text to analyze
            recipe_name: Optional name for the recipe
            
        Returns:
            RecipeAnalysis with parsed steps and metadata
        """
        logger.info(f"Analyzing recipe: {recipe_name[:50]}...")
        
        # Clean and normalize the text
        normalized_text = self._normalize_text(recipe_text)
        
        # Extract basic recipe metadata
        recipe_info = self._extract_recipe_metadata(normalized_text, recipe_name)
        
        # Split into individual steps
        raw_steps = self._split_into_steps(normalized_text)
        
        # Parse each step
        parsed_steps = []
        for i, raw_step in enumerate(raw_steps):
            step = self._parse_single_step(raw_step, i + 1)
            if step:
                parsed_steps.append(step)
        
        # Analyze dependencies between steps
        self._analyze_dependencies(parsed_steps)
        
        # Calculate complexity and duration estimates
        complexity_score = self._calculate_complexity(parsed_steps)
        estimated_duration = self._estimate_duration(parsed_steps)
        required_capabilities = self._extract_required_capabilities(parsed_steps)
        
        return RecipeAnalysis(
            recipe_name=recipe_info["name"],
            description=recipe_info["description"],
            steps=parsed_steps,
            total_steps=len(parsed_steps),
            complexity_score=complexity_score,
            estimated_duration=estimated_duration,
            required_capabilities=required_capabilities,
            recipe_type=self._classify_recipe_type(parsed_steps)
        )
    
    def analyze_csv_recipes(self, csv_data: List[Dict[str, str]]) -> List[RecipeAnalysis]:
        """
        Analyze multiple recipes from CSV data.
        
        Args:
            csv_data: List of dictionaries with recipe information
            
        Returns:
            List of RecipeAnalysis objects
        """
        results = []
        
        for row in csv_data:
            # Handle different CSV column naming conventions
            recipe_name = (
                row.get('recipe_name') or 
                row.get('name') or 
                row.get('title') or 
                f"Recipe_{len(results) + 1}"
            )
            
            recipe_text = (
                row.get('recipe_text') or 
                row.get('description') or 
                row.get('steps') or 
                row.get('content', '')
            )
            
            if recipe_text.strip():
                try:
                    analysis = self.analyze_recipe(recipe_text, recipe_name)
                    results.append(analysis)
                except Exception as e:
                    logger.error(f"Failed to analyze recipe {recipe_name}: {e}")
                    continue
        
        return results
    
    def _normalize_text(self, text: str) -> str:
        """Clean and normalize recipe text."""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[.]{2,}', '.', text)
        text = re.sub(r'[!]{2,}', '!', text)
        
        # Normalize line breaks and bullets
        text = re.sub(r'\n\s*[-*•]\s*', '\n', text)
        text = re.sub(r'\n\s*\d+\.\s*', '\n', text)
        
        return text.strip()
    
    def _extract_recipe_metadata(self, text: str, name: str) -> Dict[str, str]:
        """Extract basic metadata from recipe text."""
        lines = text.split('\n')
        
        # If no name provided, try to extract from first line
        if not name and lines:
            first_line = lines[0].strip()
            if len(first_line) < 100:  # Likely a title
                name = first_line
        
        # Extract description (first paragraph or first few lines)
        description_lines = []
        for line in lines[:3]:
            if line.strip() and len(line.strip()) > 20:
                description_lines.append(line.strip())
        
        description = ' '.join(description_lines)[:200]
        
        return {
            "name": name or "Untitled Recipe",
            "description": description or "No description available"
        }
    
    def _split_into_steps(self, text: str) -> List[str]:
        """Split recipe text into individual steps."""
        # Try different splitting strategies
        
        # Strategy 1: Numbered steps (1. 2. 3.)
        numbered_steps = re.split(r'\n\s*\d+\.\s*', text)
        if len(numbered_steps) > 2:
            return [step.strip() for step in numbered_steps[1:] if step.strip()]
        
        # Strategy 2: Bullet points or dashes
        bullet_steps = re.split(r'\n\s*[-*•]\s*', text)
        if len(bullet_steps) > 2:
            return [step.strip() for step in bullet_steps[1:] if step.strip()]
        
        # Strategy 3: Line breaks with action verbs
        lines = text.split('\n')
        steps = []
        current_step = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line starts with an action verb
            if self._starts_with_action_verb(line) and current_step:
                steps.append(' '.join(current_step))
                current_step = [line]
            else:
                current_step.append(line)
        
        if current_step:
            steps.append(' '.join(current_step))
        
        # Strategy 4: Sentence-based splitting if no clear structure
        if len(steps) < 2:
            sentences = re.split(r'[.!?]+\s+', text)
            steps = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        return steps
    
    def _parse_single_step(self, raw_text: str, order: int) -> Optional[ParsedStep]:
        """Parse a single step from raw text."""
        if not raw_text.strip():
            return None
        
        # Generate step ID
        step_id = f"step_{order}"
        
        # Extract action verbs
        action_verbs = self._extract_action_verbs(raw_text)
        
        # Classify step type based on content
        step_type = self._classify_step_type(raw_text, action_verbs)
        
        # Extract entities and parameters
        entities = self._extract_entities(raw_text)
        parameters = self._extract_parameters(raw_text)
        
        # Generate step name (first 50 chars or first sentence)
        name = self._generate_step_name(raw_text)
        
        # Calculate confidence based on clarity of action and entities
        confidence = self._calculate_step_confidence(raw_text, action_verbs, entities)
        
        return ParsedStep(
            id=step_id,
            name=name,
            description=raw_text.strip(),
            step_type=step_type,
            order=order,
            action_verbs=action_verbs,
            entities=entities,
            parameters=parameters,
            dependencies=[],  # Will be filled in later
            confidence=confidence,
            raw_text=raw_text
        )
    
    def _starts_with_action_verb(self, text: str) -> bool:
        """Check if text starts with an action verb."""
        words = text.split()
        if not words:
            return False
        
        first_word = words[0].lower().strip('.,!?')
        return first_word in self.action_verbs
    
    def _extract_action_verbs(self, text: str) -> List[str]:
        """Extract action verbs from step text."""
        words = re.findall(r'\b\w+\b', text.lower())
        return [word for word in words if word in self.action_verbs]
    
    def _classify_step_type(self, text: str, action_verbs: List[str]) -> StepType:
        """Classify the type of step based on content."""
        text_lower = text.lower()
        
        # Priority-based classification with scoring
        scores = {
            StepType.INTEGRATION: 0,
            StepType.TRANSFORM: 0,
            StepType.VALIDATION: 0,
            StepType.CONDITION: 0,
            StepType.LOOP: 0,
            StepType.ACTION: 0
        }
        
        # Integration keywords (highest priority for data operations)
        integration_keywords = [
            'extract', 'fetch', 'get', 'retrieve', 'load', 'pull', 'query', 'select',
            'database', 'api', 'service', 'endpoint', 'request', 'response', 'call',
            'connect', 'access', 'read from', 'write to', 'insert', 'update',
            'from database', 'from api', 'from service', 'to database', 'to api'
        ]
        for keyword in integration_keywords:
            if keyword in text_lower:
                scores[StepType.INTEGRATION] += 2
        
        # Transform keywords
        transform_keywords = [
            'transform', 'convert', 'process', 'parse', 'format', 'normalize',
            'map', 'filter', 'sort', 'group', 'aggregate', 'join', 'merge',
            'to json', 'to xml', 'to csv', 'reformat', 'restructure'
        ]
        for keyword in transform_keywords:
            if keyword in text_lower:
                scores[StepType.TRANSFORM] += 2
        
        # Validation keywords (but not if it's clearly an integration)
        validation_keywords = ['validate', 'verify', 'check', 'ensure', 'confirm', 'audit', 'test']
        for keyword in validation_keywords:
            if keyword in text_lower:
                # Only score as validation if not clearly integration
                if 'from' not in text_lower and 'database' not in text_lower:
                    scores[StepType.VALIDATION] += 1
        
        # Condition keywords
        condition_keywords = ['if', 'when', 'unless', 'depending on', 'based on', 'conditional']
        for keyword in condition_keywords:
            if keyword in text_lower:
                scores[StepType.CONDITION] += 2
        
        # Loop keywords
        loop_keywords = ['for each', 'repeat', 'iterate', 'loop', 'while', 'for all', 'bulk']
        for keyword in loop_keywords:
            if keyword in text_lower:
                scores[StepType.LOOP] += 2
        
        # Action verbs boost
        action_boost_verbs = ['send', 'notify', 'create', 'delete', 'execute', 'run', 'perform']
        for verb in action_verbs:
            if verb in action_boost_verbs:
                scores[StepType.ACTION] += 1
        
        # Find the highest scoring type
        max_score = max(scores.values())
        if max_score > 0:
            for step_type, score in scores.items():
                if score == max_score:
                    return step_type
        
        # Default to action if has action verbs, otherwise unknown
        if action_verbs:
            return StepType.ACTION
        
        return StepType.UNKNOWN
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities and important nouns."""
        entities = []
        text_lower = text.lower()
        
        # Extract quoted strings (likely entity names)
        quoted = re.findall(r'"([^"]*)"', text)
        entities.extend(quoted)
        
        # Extract file paths and URLs
        paths = re.findall(r'["\']?([^\s"\']+\.[a-zA-Z0-9]{2,4})["\']?', text)
        entities.extend(paths)
        
        # Extract variables (words with underscores or camelCase)
        variables = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*[A-Z][a-zA-Z0-9_]*\b', text)
        entities.extend(variables)
        
        # Extract database/table names (common patterns)
        db_entities = re.findall(r'\b(?:table|database|collection|index)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b', text, re.IGNORECASE)
        entities.extend(db_entities)
        
        # Extract important technical nouns
        technical_nouns = [
            'customer', 'user', 'data', 'database', 'table', 'record', 'field',
            'api', 'service', 'endpoint', 'request', 'response', 'payload',
            'json', 'xml', 'csv', 'file', 'document', 'report',
            'email', 'notification', 'message', 'alert',
            'account', 'profile', 'session', 'token', 'credential',
            'order', 'transaction', 'payment', 'invoice', 'billing',
            'product', 'inventory', 'catalog', 'category',
            'workflow', 'process', 'pipeline', 'batch', 'queue'
        ]
        
        # Find technical nouns in text
        words = re.findall(r'\b[a-zA-Z]+\b', text_lower)
        for word in words:
            if word in technical_nouns:
                entities.append(word)
        
        # Extract compound technical terms
        technical_patterns = [
            r'\b(customer\s+data)\b',
            r'\b(user\s+information)\b', 
            r'\b(database\s+table)\b',
            r'\b(api\s+endpoint)\b',
            r'\b(json\s+data)\b',
            r'\b(email\s+notification)\b',
            r'\b(data\s+validation)\b',
            r'\b(file\s+processing)\b',
            r'\b(user\s+account)\b',
            r'\b(payment\s+information)\b'
        ]
        
        for pattern in technical_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            entities.extend(matches)
        
        # Extract IDs, codes, and identifiers
        id_patterns = [
            r'\b([a-zA-Z]+_id)\b',
            r'\b([a-zA-Z]+ID)\b', 
            r'\b(id\s+\d+)\b',
            r'\b([A-Z]{2,10}\d+)\b'
        ]
        
        for pattern in id_patterns:
            matches = re.findall(pattern, text)
            entities.extend(matches)
        
        # Clean and deduplicate entities
        clean_entities = []
        for entity in entities:
            if isinstance(entity, str) and len(entity.strip()) > 1:
                clean_entity = entity.strip().lower()
                # Skip common words and connectors
                if clean_entity not in ['and', 'or', 'the', 'a', 'an', 'to', 'from', 'with', 'by', 'in', 'on', 'at']:
                    clean_entities.append(clean_entity)
        
        return list(set(clean_entities))
    
    def _extract_parameters(self, text: str) -> Dict[str, Any]:
        """Extract parameters and configuration from step text."""
        parameters = {}
        
        # Extract key-value pairs
        kv_pairs = re.findall(r'(\w+)\s*[:=]\s*(["\']?)([^,"\'\n]+)\2', text)
        for key, _, value in kv_pairs:
            # Try to parse as number
            try:
                if '.' in value:
                    parameters[key] = float(value)
                else:
                    parameters[key] = int(value)
            except ValueError:
                parameters[key] = value.strip()
        
        # Extract JSON-like structures
        json_matches = re.findall(r'\{[^}]+\}', text)
        for match in json_matches:
            try:
                parsed = json.loads(match)
                parameters.update(parsed)
            except json.JSONDecodeError:
                continue
        
        return parameters
    
    def _generate_step_name(self, text: str) -> str:
        """Generate a concise name for the step."""
        # Try first sentence
        sentences = re.split(r'[.!?]+', text)
        first_sentence = sentences[0].strip()
        
        if len(first_sentence) <= 60:
            return first_sentence
        
        # Truncate to 50 characters
        if len(text) > 50:
            return text[:47] + "..."
        
        return text.strip()
    
    def _calculate_step_confidence(self, text: str, action_verbs: List[str], entities: List[str]) -> float:
        """Calculate confidence score for step parsing."""
        confidence = 0.5  # Base confidence
        
        # Boost for clear action verbs
        if action_verbs:
            confidence += 0.2
        
        # Boost for identified entities
        if entities:
            confidence += 0.1 * min(len(entities), 3)
        
        # Boost for structured text
        if re.search(r'\d+\.|\-|\*', text):
            confidence += 0.1
        
        # Penalty for very short or very long text
        text_len = len(text.split())
        if text_len < 3:
            confidence -= 0.2
        elif text_len > 50:
            confidence -= 0.1
        
        return min(1.0, max(0.1, confidence))
    
    def _analyze_dependencies(self, steps: List[ParsedStep]) -> None:
        """Analyze dependencies between steps."""
        for i, current_step in enumerate(steps):
            # Look for references to previous steps
            for j, previous_step in enumerate(steps[:i]):
                # Check if current step references entities from previous step
                if self._has_dependency(current_step, previous_step):
                    current_step.dependencies.append(previous_step.id)
    
    def _has_dependency(self, current_step: ParsedStep, previous_step: ParsedStep) -> bool:
        """Check if current step depends on previous step."""
        # Simple heuristic: check if entities from previous step appear in current step
        current_text = current_step.description.lower()
        
        for entity in previous_step.entities:
            if entity.lower() in current_text:
                return True
        
        # Check for sequential indicators
        if any(word in current_text for word in ['then', 'after', 'next', 'following', 'using']):
            return True
        
        return False
    
    def _calculate_complexity(self, steps: List[ParsedStep]) -> float:
        """Calculate overall recipe complexity score."""
        if not steps:
            return 0.0
        
        complexity = 0.0
        
        # Base complexity from number of steps
        complexity += len(steps) * 0.1
        
        # Add complexity for different step types
        type_weights = {
            StepType.ACTION: 0.1,
            StepType.CONDITION: 0.3,
            StepType.LOOP: 0.4,
            StepType.TRANSFORM: 0.2,
            StepType.VALIDATION: 0.2,
            StepType.INTEGRATION: 0.3,
            StepType.UNKNOWN: 0.05
        }
        
        for step in steps:
            complexity += type_weights.get(step.step_type, 0.1)
        
        # Add complexity for dependencies
        total_dependencies = sum(len(step.dependencies) for step in steps)
        complexity += total_dependencies * 0.1
        
        # Normalize to 0-1 scale
        return min(1.0, complexity / len(steps))
    
    def _estimate_duration(self, steps: List[ParsedStep]) -> Optional[int]:
        """Estimate execution duration in minutes."""
        if not steps:
            return None
        
        total_minutes = 0
        
        # Base time per step type (in minutes)
        step_times = {
            StepType.ACTION: 2,
            StepType.CONDITION: 1,
            StepType.LOOP: 5,
            StepType.TRANSFORM: 3,
            StepType.VALIDATION: 1,
            StepType.INTEGRATION: 4,
            StepType.UNKNOWN: 2
        }
        
        for step in steps:
            base_time = step_times.get(step.step_type, 2)
            
            # Adjust based on complexity indicators
            if len(step.entities) > 3:
                base_time *= 1.5
            if len(step.parameters) > 2:
                base_time *= 1.3
            if len(step.dependencies) > 1:
                base_time *= 1.2
            
            total_minutes += base_time
        
        return int(total_minutes)
    
    def _extract_required_capabilities(self, steps: List[ParsedStep]) -> List[str]:
        """Extract required capabilities from steps."""
        capabilities = set()
        
        for step in steps:
            # Add capabilities based on step type
            if step.step_type == StepType.INTEGRATION:
                capabilities.add("api-integration")
            elif step.step_type == StepType.TRANSFORM:
                capabilities.add("data-transformation")
            elif step.step_type == StepType.VALIDATION:
                capabilities.add("data-validation")
            elif step.step_type == StepType.LOOP:
                capabilities.add("iteration")
            elif step.step_type == StepType.CONDITION:
                capabilities.add("conditional-logic")
            
            # Add capabilities based on entities
            for entity in step.entities:
                if any(ext in entity.lower() for ext in ['.json', '.xml', '.csv']):
                    capabilities.add("file-processing")
                elif 'database' in entity.lower() or 'table' in entity.lower():
                    capabilities.add("database-access")
                elif 'http' in entity.lower() or 'url' in entity.lower():
                    capabilities.add("web-requests")
        
        return list(capabilities)
    
    def _classify_recipe_type(self, steps: List[ParsedStep]) -> str:
        """Classify the overall recipe type."""
        if not steps:
            return "unknown"
        
        # Count step types
        type_counts = {}
        for step in steps:
            type_counts[step.step_type] = type_counts.get(step.step_type, 0) + 1
        
        total_steps = len(steps)
        
        # Classification logic
        if type_counts.get(StepType.INTEGRATION, 0) / total_steps > 0.5:
            return "integration"
        elif type_counts.get(StepType.TRANSFORM, 0) / total_steps > 0.4:
            return "data-processing"
        elif type_counts.get(StepType.VALIDATION, 0) / total_steps > 0.3:
            return "validation"
        elif type_counts.get(StepType.LOOP, 0) > 0:
            return "automation"
        else:
            return "workflow"
    
    def _compile_step_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for step recognition."""
        return {
            'numbered': re.compile(r'^\s*\d+\.\s*'),
            'bulleted': re.compile(r'^\s*[-*•]\s*'),
            'action_start': re.compile(r'^\s*[A-Z][a-z]+\s+'),
        }
    
    def _load_action_verbs(self) -> set:
        """Load common action verbs for step identification."""
        return {
            # Data operations
            'extract', 'load', 'fetch', 'get', 'retrieve', 'read', 'download', 'import',
            'save', 'store', 'write', 'export', 'upload', 'persist',
            'transform', 'convert', 'process', 'parse', 'format', 'normalize',
            'filter', 'sort', 'group', 'aggregate', 'join', 'merge',
            
            # Control flow
            'check', 'verify', 'validate', 'ensure', 'confirm', 'test',
            'if', 'when', 'while', 'for', 'repeat', 'loop', 'iterate',
            'call', 'invoke', 'execute', 'run', 'perform', 'do',
            
            # Communication
            'send', 'receive', 'request', 'response', 'post', 'put', 'delete',
            'notify', 'alert', 'email', 'message', 'broadcast',
            
            # Management
            'create', 'update', 'delete', 'modify', 'edit', 'change',
            'add', 'remove', 'insert', 'append', 'prepend',
            'start', 'stop', 'pause', 'resume', 'restart',
            
            # Analysis
            'analyze', 'calculate', 'compute', 'evaluate', 'assess',
            'compare', 'match', 'find', 'search', 'lookup', 'query'
        }
    
    def _compile_entity_patterns(self) -> Dict[str, re.Pattern]:
        """Compile patterns for entity extraction."""
        return {
            'quoted': re.compile(r'"([^"]*)"'),
            'files': re.compile(r'["\']?([^\s"\']+\.[a-zA-Z0-9]{2,4})["\']?'),
            'variables': re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]*[A-Z][a-zA-Z0-9_]*\b'),
            'database': re.compile(r'\b(?:table|database|collection|index)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b', re.IGNORECASE),
        }
    
    def _compile_dependency_patterns(self) -> Dict[str, re.Pattern]:
        """Compile patterns for dependency detection."""
        return {
            'sequential': re.compile(r'\b(?:then|after|next|following|using)\b', re.IGNORECASE),
            'conditional': re.compile(r'\b(?:if|when|unless|provided)\b', re.IGNORECASE),
        }