"""
Python Notebook Generator for ThinkForge

This module converts DSL workflows into Jupyter notebook format, allowing
users to see, modify, and execute workflow steps as Python code cells
in a transparent and debuggable environment.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .models import Text2SQLCache


class CellType(str, Enum):
    """Jupyter notebook cell types"""
    CODE = "code"
    MARKDOWN = "markdown"
    RAW = "raw"


@dataclass
class NotebookCell:
    """Represents a Jupyter notebook cell"""
    cell_type: CellType
    source: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_count: Optional[int] = None
    outputs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Jupyter notebook cell format"""
        cell_data = {
            "cell_type": self.cell_type.value,
            "metadata": self.metadata,
            "source": self.source
        }
        
        if self.cell_type == CellType.CODE:
            cell_data["execution_count"] = self.execution_count
            cell_data["outputs"] = self.outputs
            
        return cell_data


@dataclass
class StepCodeTemplate:
    """Template for generating code for a workflow step"""
    setup_code: List[str]
    execution_code: List[str] 
    validation_code: List[str]
    imports: List[str]
    description: str
    step_type: str
    
    
class PythonNotebookGenerator:
    """
    Generates Jupyter notebooks from ThinkForge DSL workflows.
    
    Converts workflow steps into multi-cell Python code with proper
    variable passing, error handling, and documentation.
    """

    def __init__(self):
        """Initialize the notebook generator."""
        self.step_templates = self._initialize_step_templates()

    def generate_notebook(
        self,
        workflow_dsl: Dict[str, Any],
        workflow_name: str = "Generated Workflow",
        include_documentation: bool = True,
        add_setup_cells: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a Jupyter notebook from workflow DSL.

        Args:
            workflow_dsl: The workflow DSL dictionary
            workflow_name: Name for the notebook
            include_documentation: Whether to include markdown documentation
            add_setup_cells: Whether to add initial setup cells

        Returns:
            Jupyter notebook as dictionary
        """
        cells = []
        
        # Add header documentation
        if include_documentation:
            cells.extend(self._create_header_cells(workflow_name, workflow_dsl))
        
        # Add setup cells
        if add_setup_cells:
            cells.extend(self._create_setup_cells(workflow_dsl))
        
        # Process workflow steps
        workflow = workflow_dsl.get("workflow", {})
        steps = workflow.get("steps", [])
        edges = workflow.get("edges", [])
        
        # Build dependency graph for variable passing
        dependency_graph = self._build_dependency_graph(steps, edges)
        
        # Generate cells for each step
        for i, step in enumerate(steps):
            step_cells = self._generate_step_cells(
                step, 
                i + 1, 
                dependency_graph.get(step["id"], []),
                include_documentation
            )
            cells.extend(step_cells)
        
        # Add conclusion cells
        if include_documentation:
            cells.extend(self._create_conclusion_cells(workflow_dsl))
        
        # Create notebook structure
        notebook = {
            "cells": [cell.to_dict() for cell in cells],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3 (ThinkForge)",
                    "language": "python",
                    "name": "thinkforge-python3"
                },
                "language_info": {
                    "name": "python",
                    "version": "3.9.0",
                    "mimetype": "text/x-python",
                    "codemirror_mode": {
                        "name": "ipython",
                        "version": 3
                    },
                    "pygments_lexer": "ipython3",
                    "nbconvert_exporter": "python",
                    "file_extension": ".py"
                },
                "thinkforge": {
                    "workflow_id": workflow.get("id"),
                    "workflow_name": workflow_name,
                    "generated_at": datetime.now().isoformat(),
                    "generator_version": "1.0.0"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 4
        }
        
        return notebook

    def _create_header_cells(self, workflow_name: str, workflow_dsl: Dict[str, Any]) -> List[NotebookCell]:
        """Create header documentation cells"""
        cells = []
        
        # Main title
        title_cell = NotebookCell(
            cell_type=CellType.MARKDOWN,
            source=[f"# {workflow_name}\n"],
            metadata={"tags": ["header"]}
        )
        cells.append(title_cell)
        
        # Workflow information
        workflow = workflow_dsl.get("workflow", {})
        info_lines = [
            "## Workflow Information\n",
            "\n",
            f"- **Type**: {workflow.get('type', 'Unknown')}\n",
            f"- **Version**: {workflow.get('version', '1.0')}\n",
            f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"- **Total Steps**: {len(workflow.get('steps', []))}\n",
            "\n",
            "---\n"
        ]
        
        info_cell = NotebookCell(
            cell_type=CellType.MARKDOWN,
            source=info_lines,
            metadata={"tags": ["info"]}
        )
        cells.append(info_cell)
        
        return cells

    def _create_setup_cells(self, workflow_dsl: Dict[str, Any]) -> List[NotebookCell]:
        """Create initial setup cells for imports and configuration"""
        cells = []
        
        # Setup documentation
        setup_doc = NotebookCell(
            cell_type=CellType.MARKDOWN,
            source=[
                "## Environment Setup\n",
                "\n",
                "This section sets up the Python environment with required imports and configurations.\n"
            ],
            metadata={"tags": ["setup"]}
        )
        cells.append(setup_doc)
        
        # Analyze workflow to determine required imports
        workflow = workflow_dsl.get("workflow", {})
        steps = workflow.get("steps", [])
        required_imports = set()
        
        for step in steps:
            step_type = step.get("type", "").lower()
            imports = self._get_imports_for_step_type(step_type)
            required_imports.update(imports)
        
        # Standard imports cell
        standard_imports = [
            "# Standard library imports\n",
            "import json\n",
            "import os\n",
            "import sys\n",
            "from datetime import datetime\n",
            "from typing import Dict, List, Any, Optional\n",
            "\n",
            "# Third-party imports\n"
        ]
        
        # Add step-specific imports
        for import_line in sorted(required_imports):
            standard_imports.append(f"{import_line}\n")
        
        standard_imports.extend([
            "\n",
            "# Workflow execution tracking\n",
            "workflow_results = {}\n",
            "execution_log = []\n",
            "\n",
            "def log_step(step_id, status, message=None, result=None):\n",
            "    \"\"\"Log step execution for tracking\"\"\"\n",
            "    log_entry = {\n",
            "        'step_id': step_id,\n",
            "        'status': status,\n",
            "        'timestamp': datetime.now().isoformat(),\n",
            "        'message': message\n",
            "    }\n",
            "    if result is not None:\n",
            "        log_entry['result_type'] = type(result).__name__\n",
            "        if hasattr(result, '__len__'):\n",
            "            log_entry['result_size'] = len(result)\n",
            "    execution_log.append(log_entry)\n",
            "    print(f\"📋 {step_id}: {status}\" + (f\" - {message}\" if message else \"\"))\n",
            "\n",
            "print(\"✅ Environment setup complete\")\n"
        ])
        
        imports_cell = NotebookCell(
            cell_type=CellType.CODE,
            source=standard_imports,
            metadata={"tags": ["setup", "imports"]}
        )
        cells.append(imports_cell)
        
        return cells

    def _generate_step_cells(
        self, 
        step: Dict[str, Any], 
        step_number: int,
        dependencies: List[str],
        include_documentation: bool
    ) -> List[NotebookCell]:
        """Generate cells for a single workflow step"""
        cells = []
        step_id = step.get("id", f"step_{step_number}")
        step_type = step.get("type", "unknown").lower()
        step_name = step.get("name", f"Step {step_number}")
        
        # Step documentation
        if include_documentation:
            doc_lines = [
                f"## Step {step_number}: {step_name}\n",
                "\n",
                f"**Type**: {step_type}\n",
                f"**ID**: `{step_id}`\n",
            ]
            
            if dependencies:
                doc_lines.extend([
                    f"**Dependencies**: {', '.join(dependencies)}\n",
                ])
            
            if step.get("description"):
                doc_lines.extend([
                    "\n",
                    f"**Description**: {step['description']}\n"
                ])
            
            doc_lines.append("\n")
            
            doc_cell = NotebookCell(
                cell_type=CellType.MARKDOWN,
                source=doc_lines,
                metadata={"tags": ["step", f"step-{step_number}"]}
            )
            cells.append(doc_cell)
        
        # Generate code template for this step type
        template = self._generate_step_template(step, step_number, dependencies)
        
        # Setup cell
        if template.setup_code:
            setup_cell = NotebookCell(
                cell_type=CellType.CODE,
                source=template.setup_code,
                metadata={
                    "tags": ["step", f"step-{step_number}", "setup"],
                    "step_id": step_id,
                    "step_type": step_type
                }
            )
            cells.append(setup_cell)
        
        # Execution cell
        execution_cell = NotebookCell(
            cell_type=CellType.CODE,
            source=template.execution_code,
            metadata={
                "tags": ["step", f"step-{step_number}", "execution"],
                "step_id": step_id,
                "step_type": step_type
            }
        )
        cells.append(execution_cell)
        
        # Validation cell
        if template.validation_code:
            validation_cell = NotebookCell(
                cell_type=CellType.CODE,
                source=template.validation_code,
                metadata={
                    "tags": ["step", f"step-{step_number}", "validation"],
                    "step_id": step_id,
                    "step_type": step_type
                }
            )
            cells.append(validation_cell)
        
        return cells

    def _generate_step_template(
        self, 
        step: Dict[str, Any], 
        step_number: int,
        dependencies: List[str]
    ) -> StepCodeTemplate:
        """Generate code template for a specific step"""
        step_type = step.get("type", "unknown").lower()
        step_id = step.get("id", f"step_{step_number}")
        
        # Get base template for step type
        if step_type in self.step_templates:
            base_template = self.step_templates[step_type]
            return self._customize_template(base_template, step, step_number, dependencies)
        else:
            # Generic template for unknown step types
            return self._create_generic_template(step, step_number, dependencies)

    def _customize_template(
        self,
        base_template: StepCodeTemplate,
        step: Dict[str, Any],
        step_number: int,
        dependencies: List[str]
    ) -> StepCodeTemplate:
        """Customize a base template with step-specific data"""
        step_id = step.get("id", f"step_{step_number}")
        template = step.get("template", "")
        cache_id = step.get("cache_id")
        
        # Customize setup code
        setup_code = []
        for line in base_template.setup_code:
            customized_line = line.format(
                step_id=step_id,
                step_number=step_number,
                template=template,
                cache_id=cache_id,
                **step.get("parameters", {})
            )
            setup_code.append(customized_line)
        
        # Add dependency variables
        if dependencies:
            setup_code.extend([
                "\n",
                "# Get results from dependent steps\n"
            ])
            for dep in dependencies:
                setup_code.append(f"{dep}_result = workflow_results.get('{dep}')\n")
        
        # Customize execution code
        execution_code = []
        for line in base_template.execution_code:
            customized_line = line.format(
                step_id=step_id,
                step_number=step_number,
                template=template,
                cache_id=cache_id,
                **step.get("parameters", {})
            )
            execution_code.append(customized_line)
        
        # Customize validation code
        validation_code = []
        for line in base_template.validation_code:
            customized_line = line.format(
                step_id=step_id,
                step_number=step_number,
                template=template,
                **step.get("parameters", {})
            )
            validation_code.append(customized_line)
        
        return StepCodeTemplate(
            setup_code=setup_code,
            execution_code=execution_code,
            validation_code=validation_code,
            imports=base_template.imports,
            description=base_template.description,
            step_type=base_template.step_type
        )

    def _create_generic_template(
        self,
        step: Dict[str, Any],
        step_number: int,
        dependencies: List[str]
    ) -> StepCodeTemplate:
        """Create a generic template for unknown step types"""
        step_id = step.get("id", f"step_{step_number}")
        template = step.get("template", "")
        
        setup_code = [
            f"# Step {step_number}: Generic execution\n",
            f"step_id = '{step_id}'\n",
            f"template = '''{template}'''\n",
            "\n"
        ]
        
        if dependencies:
            setup_code.extend([
                "# Get results from dependent steps\n"
            ])
            for dep in dependencies:
                setup_code.append(f"{dep}_result = workflow_results.get('{dep}')\n")
        
        execution_code = [
            "try:\n",
            "    log_step(step_id, 'started')\n",
            "    \n",
            "    # Generic step execution - template processing\n",
            f"    {step_id}_result = {{\n",
            "        'template': template,\n",
            "        'step_type': 'generic',\n",
            "        'processed': True,\n",
            "        'timestamp': datetime.now().isoformat()\n",
            "    }\n",
            "    \n",
            f"    workflow_results['{step_id}'] = {step_id}_result\n",
            "    log_step(step_id, 'completed', 'Generic step executed')\n",
            "    \n",
            "except Exception as e:\n",
            "    log_step(step_id, 'failed', str(e))\n",
            "    raise\n"
        ]
        
        validation_code = [
            f"# Validate {step_id} results\n",
            f"if '{step_id}' in workflow_results:\n",
            f"    result = workflow_results['{step_id}']\n",
            "    print(f\"✅ Step completed successfully\")\n",
            "    print(f\"📊 Result type: {type(result).__name__}\")\n",
            "    if isinstance(result, dict):\n",
            "        print(f\"📊 Result keys: {list(result.keys())}\")\n",
            "else:\n",
            f"    print(f\"❌ No result found for {step_id}\")\n"
        ]
        
        return StepCodeTemplate(
            setup_code=setup_code,
            execution_code=execution_code,
            validation_code=validation_code,
            imports=[],
            description=f"Generic execution for {step.get('type', 'unknown')} step",
            step_type="generic"
        )

    def _initialize_step_templates(self) -> Dict[str, StepCodeTemplate]:
        """Initialize templates for different step types"""
        templates = {}
        
        # API step template
        templates["api"] = StepCodeTemplate(
            setup_code=[
                "# Step {step_number}: API Call Setup\n",
                "step_id = '{step_id}'\n",
                "\n",
                "# Parse API configuration\n",
                "template = '''{template}'''\n",
                "try:\n",
                "    if template.startswith('{'):\n",
                "        api_config = json.loads(template)\n",
                "        url = api_config.get('url')\n",
                "        method = api_config.get('method', 'GET').upper()\n",
                "        headers = api_config.get('headers', {{}})\n",
                "        params = api_config.get('params', {{}})\n",
                "        data = api_config.get('data')\n",
                "        timeout = api_config.get('timeout', 30)\n",
                "    else:\n",
                "        # Simple URL\n",
                "        url = template\n",
                "        method = 'GET'\n",
                "        headers = {{}}\n",
                "        params = {{}}\n",
                "        data = None\n",
                "        timeout = 30\n",
                "except json.JSONDecodeError:\n",
                "    # Treat as simple URL\n",
                "    url = template\n",
                "    method = 'GET'\n",
                "    headers = {{}}\n",
                "    params = {{}}\n",
                "    data = None\n",
                "    timeout = 30\n",
                "\n",
                "print(f\"🌐 API Call: {{method}} {{url}}\")\n"
            ],
            execution_code=[
                "try:\n",
                "    log_step(step_id, 'started', f'Making {{method}} request to {{url}}')\n",
                "    \n",
                "    # Make API request\n",
                "    if data and isinstance(data, (dict, list)):\n",
                "        headers['Content-Type'] = headers.get('Content-Type', 'application/json')\n",
                "        response = requests.request(\n",
                "            method=method,\n",
                "            url=url,\n",
                "            headers=headers,\n",
                "            params=params,\n",
                "            json=data,\n",
                "            timeout=timeout\n",
                "        )\n",
                "    else:\n",
                "        response = requests.request(\n",
                "            method=method,\n",
                "            url=url,\n",
                "            headers=headers,\n",
                "            params=params,\n",
                "            data=data,\n",
                "            timeout=timeout\n",
                "        )\n",
                "    \n",
                "    # Process response\n",
                "    response.raise_for_status()\n",
                "    \n",
                "    try:\n",
                "        response_data = response.json()\n",
                "    except ValueError:\n",
                "        response_data = response.text\n",
                "    \n",
                f"    {step_id}_result = {{\n",
                "        'status': response.status_code,\n",
                "        'headers': dict(response.headers),\n",
                "        'data': response_data,\n",
                "        'url': str(response.url)\n",
                "    }\n",
                "    \n",
                f"    workflow_results['{step_id}'] = {step_id}_result\n",
                "    log_step(step_id, 'completed', f'API call successful ({{response.status_code}})')\n",
                "    \n",
                "except requests.exceptions.RequestException as e:\n",
                "    log_step(step_id, 'failed', f'API request failed: {{str(e)}}')\n",
                "    raise\n",
                "except Exception as e:\n",
                "    log_step(step_id, 'failed', f'Unexpected error: {{str(e)}}')\n",
                "    raise\n"
            ],
            validation_code=[
                f"# Validate API response for {step_id}\n",
                f"if '{step_id}' in workflow_results:\n",
                f"    result = workflow_results['{step_id}']\n",
                "    print(f\"✅ API call completed successfully\")\n",
                "    print(f\"📊 Status Code: {{result['status']}}\")\n",
                "    print(f\"📊 Response Type: {{type(result['data']).__name__}}\")\n",
                "    \n",
                "    if isinstance(result['data'], dict):\n",
                "        print(f\"📊 Response Keys: {{list(result['data'].keys())}}\")\n",
                "    elif isinstance(result['data'], str):\n",
                "        print(f\"📊 Response Length: {{len(result['data'])}} characters\")\n",
                "    \n",
                "    # Display formatted response (limited)\n",
                "    if isinstance(result['data'], dict):\n",
                "        import pprint\n",
                "        print(\"\\n📋 Response Preview:\")\n",
                "        pprint.pprint(result['data'], depth=2, width=80)\n",
                "    elif isinstance(result['data'], str) and len(result['data']) < 500:\n",
                "        print(f\"\\n📋 Response: {{result['data']}}\")\n",
                "else:\n",
                f"    print(f\"❌ No result found for {{step_id}}\")\n"
            ],
            imports=["import requests", "import json", "import pprint"],
            description="Execute HTTP API calls with comprehensive error handling",
            step_type="api"
        )
        
        # SQL step template
        templates["sql"] = StepCodeTemplate(
            setup_code=[
                "# Step {step_number}: SQL Query Setup\n",
                "step_id = '{step_id}'\n",
                "sql_query = '''{template}'''\n",
                "\n",
                "# Database connection configuration\n",
                "database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/thinkforge')\n",
                "print(f\"🗄️ SQL Query: {{sql_query[:100]}}{'...' if len(sql_query) > 100 else ''}\")\n"
            ],
            execution_code=[
                "try:\n",
                "    log_step(step_id, 'started', 'Executing SQL query')\n",
                "    \n",
                "    # Execute SQL query using pandas for easier result handling\n",
                "    from sqlalchemy import create_engine\n",
                "    engine = create_engine(database_url)\n",
                "    \n",
                "    # Execute query and get results as DataFrame\n",
                "    df = pd.read_sql_query(sql_query, engine)\n",
                "    \n",
                f"    {step_id}_result = {{\n",
                "        'columns': df.columns.tolist(),\n",
                "        'rows': df.to_dict('records'),\n",
                "        'row_count': len(df),\n",
                "        'query': sql_query\n",
                "    }\n",
                "    \n",
                f"    workflow_results['{step_id}'] = {step_id}_result\n",
                "    log_step(step_id, 'completed', f'Query returned {{len(df)}} rows')\n",
                "    \n",
                "except Exception as e:\n",
                "    log_step(step_id, 'failed', f'SQL query failed: {{str(e)}}')\n",
                "    raise\n"
            ],
            validation_code=[
                f"# Validate SQL query results for {step_id}\n",
                f"if '{step_id}' in workflow_results:\n",
                f"    result = workflow_results['{step_id}']\n",
                "    print(f\"✅ SQL query completed successfully\")\n",
                "    print(f\"📊 Rows returned: {{result['row_count']}}\")\n",
                "    print(f\"📊 Columns: {{', '.join(result['columns'])}}\")\n",
                "    \n",
                "    # Display sample data\n",
                "    if result['rows']:\n",
                "        print(\"\\n📋 Sample Data (first 5 rows):\")\n",
                "        sample_df = pd.DataFrame(result['rows'][:5])\n",
                "        print(sample_df.to_string(index=False))\n",
                "    else:\n",
                "        print(\"\\n📋 No data returned\")\n",
                "else:\n",
                f"    print(f\"❌ No result found for {{step_id}}\")\n"
            ],
            imports=["import pandas as pd", "from sqlalchemy import create_engine"],
            description="Execute SQL queries with result formatting",
            step_type="sql"
        )
        
        # Function step template
        templates["function"] = StepCodeTemplate(
            setup_code=[
                "# Step {step_number}: Function Execution Setup\n",
                "step_id = '{step_id}'\n",
                "\n",
                "# Function code\n",
                "function_code = '''{template}'''\n",
                "print(f\"🔧 Executing custom function...\")\n"
            ],
            execution_code=[
                "try:\n",
                "    log_step(step_id, 'started', 'Executing custom function')\n",
                "    \n",
                "    # Create execution namespace with safe builtins\n",
                "    namespace = {{\n",
                "        '__builtins__': {{\n",
                "            'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,\n",
                "            'list': list, 'dict': dict, 'tuple': tuple, 'set': set,\n",
                "            'range': range, 'enumerate': enumerate, 'zip': zip,\n",
                "            'sum': sum, 'min': min, 'max': max, 'abs': abs, 'round': round,\n",
                "            'print': print, 'type': type, 'isinstance': isinstance\n",
                "        }},\n",
                "        'json': json,\n",
                "        'datetime': datetime,\n",
                "        'workflow_results': workflow_results\n",
                "    }}\n",
                "    \n",
                "    # Add dependency results to namespace\n",
                "    for dep_id, dep_result in workflow_results.items():\n",
                "        namespace[f'{{dep_id}}_result'] = dep_result\n",
                "    \n",
                "    # Execute function code\n",
                "    exec(function_code, namespace)\n",
                "    \n",
                "    # Get result from execute function or result variable\n",
                "    if 'execute' in namespace:\n",
                "        inputs = {{k: v for k, v in workflow_results.items()}}\n",
                f"        {step_id}_result = namespace['execute'](inputs)\n",
                "    elif 'result' in namespace:\n",
                f"        {step_id}_result = namespace['result']\n",
                "    else:\n",
                f"        {step_id}_result = {{\n",
                "            'message': 'Function executed successfully',\n",
                "            'namespace_keys': [k for k in namespace.keys() if not k.startswith('__')]\n",
                "        }\n",
                "    \n",
                f"    workflow_results['{step_id}'] = {step_id}_result\n",
                "    log_step(step_id, 'completed', 'Function executed successfully')\n",
                "    \n",
                "except Exception as e:\n",
                "    log_step(step_id, 'failed', f'Function execution failed: {{str(e)}}')\n",
                "    raise\n"
            ],
            validation_code=[
                f"# Validate function results for {step_id}\n",
                f"if '{step_id}' in workflow_results:\n",
                f"    result = workflow_results['{step_id}']\n",
                "    print(f\"✅ Function executed successfully\")\n",
                "    print(f\"📊 Result type: {{type(result).__name__}}\")\n",
                "    \n",
                "    # Display result based on type\n",
                "    if isinstance(result, dict):\n",
                "        print(f\"📊 Result keys: {{list(result.keys())}}\")\n",
                "        if len(str(result)) < 500:\n",
                "            import pprint\n",
                "            print(\"\\n📋 Result:\")\n",
                "            pprint.pprint(result)\n",
                "    elif isinstance(result, (list, tuple)):\n",
                "        print(f\"📊 Result length: {{len(result)}}\")\n",
                "        if len(result) <= 10:\n",
                "            print(f\"\\n📋 Result: {{result}}\")\n",
                "    else:\n",
                "        print(f\"\\n📋 Result: {{result}}\")\n",
                "else:\n",
                f"    print(f\"❌ No result found for {{step_id}}\")\n"
            ],
            imports=["import json"],
            description="Execute custom Python functions in controlled environment",
            step_type="function"
        )
        
        return templates

    def _build_dependency_graph(self, steps: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build dependency graph from workflow edges"""
        dependencies = {}
        
        for edge in edges:
            source = edge.get("from")
            target = edge.get("to")
            
            if target not in dependencies:
                dependencies[target] = []
            
            if source and source != "start":
                dependencies[target].append(source)
        
        return dependencies

    def _get_imports_for_step_type(self, step_type: str) -> List[str]:
        """Get required imports for a step type"""
        if step_type in self.step_templates:
            return self.step_templates[step_type].imports
        return []

    def _create_conclusion_cells(self, workflow_dsl: Dict[str, Any]) -> List[NotebookCell]:
        """Create conclusion cells for the notebook"""
        cells = []
        
        # Workflow summary
        summary_cell = NotebookCell(
            cell_type=CellType.MARKDOWN,
            source=[
                "## Workflow Summary\n",
                "\n",
                "The workflow execution is complete. Below is a summary of all steps and their results.\n"
            ],
            metadata={"tags": ["conclusion"]}
        )
        cells.append(summary_cell)
        
        # Results summary code
        summary_code = [
            "# Workflow Execution Summary\n",
            "print(\"🎉 Workflow Execution Complete!\")\n",
            "print(\"=\" * 50)\n",
            "\n",
            "print(f\"📊 Total Steps: {len(workflow_results)}\")\n",
            "print(f\"📊 Total Log Entries: {len(execution_log)}\")\n",
            "\n",
            "# Status summary\n",
            "status_counts = {}\n",
            "for log_entry in execution_log:\n",
            "    status = log_entry['status']\n",
            "    status_counts[status] = status_counts.get(status, 0) + 1\n",
            "\n",
            "print(\"\\n📈 Execution Status:\")\n",
            "for status, count in status_counts.items():\n",
            "    print(f\"  - {status}: {count}\")\n",
            "\n",
            "# Results overview\n",
            "print(\"\\n📋 Step Results:\")\n",
            "for step_id, result in workflow_results.items():\n",
            "    result_type = type(result).__name__\n",
            "    if hasattr(result, '__len__'):\n",
            "        print(f\"  - {step_id}: {result_type} (size: {len(result)})\")\n",
            "    else:\n",
            "        print(f\"  - {step_id}: {result_type}\")\n",
            "\n",
            "print(\"\\n✅ Workflow completed successfully!\")\n"
        ]
        
        summary_code_cell = NotebookCell(
            cell_type=CellType.CODE,
            source=summary_code,
            metadata={"tags": ["conclusion", "summary"]}
        )
        cells.append(summary_code_cell)
        
        return cells