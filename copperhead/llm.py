"""
Copperhead LLM Integration Module

This module provides natural language to code generation using Ollama coding LLMs.
Users can describe what they want in plain English, and the LLM will:
1. Parse the description and identify ambiguities
2. Search existing modules in the registry for reusable code
3. Generate Copperhead code with proper patterns
4. Generate comprehensive tests
5. Validate and debug the code before compilation
6. Iterate and refine until the goal is met
"""

import json
import subprocess
import re
import ast
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum, auto

from .registry import ModuleRegistry, ModuleMetadata, FunctionSignature, get_registry
from .debugger import CopperheadDebugger, CodeValidator, DebugResult


class GenerationStatus(Enum):
    """Status of code generation."""
    PENDING = auto()
    GENERATING = auto()
    VALIDATING = auto()
    REFINDING = auto()
    SUCCESS = auto()
    FAILED = auto()


class AmbiguityLevel(Enum):
    """Level of ambiguity in the description."""
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


@dataclass
class Ambiguity:
    """Represents an ambiguity in the user's description."""
    question: str
    context: str
    options: List[str]
    recommendation: str


@dataclass
class GeneratedCode:
    """Generated code result."""
    source_code: str
    tests_code: str
    description: str
    ambiguities: List[Ambiguity] = field(default_factory=list)
    status: GenerationStatus = GenerationStatus.PENDING
    error_message: Optional[str] = None
    iteration: int = 0
    used_modules: List[str] = field(default_factory=list)
    debug_result: Optional[DebugResult] = None


@dataclass
class GenerationResult:
    """Result of the generation process."""
    success: bool
    code: Optional[GeneratedCode] = None
    iterations: int = 0
    errors: List[str] = field(default_factory=list)


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, model: str = "maryasov/qwen2.5-coder-cline:latest"):
        self.model = model
        self.base_url = "http://localhost:11434"
    
    def generate(self, prompt: str, system: str = "") -> str:
        """Generate a response from the LLM."""
        try:
            # Use ollama CLI for generation
            full_prompt = prompt
            if system:
                full_prompt = f"{system}\n\n{prompt}"
            
            result = subprocess.run(
                ["ollama", "run", self.model, full_prompt],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Ollama error: {result.stderr}")
            
            return result.stdout.strip()
        
        except subprocess.TimeoutExpired:
            raise RuntimeError("Ollama generation timed out (120s limit)")
        except FileNotFoundError:
            raise RuntimeError("Ollama not found. Please install Ollama first.")
    
    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False


class CopperheadCoder:
    """LLM-powered Copperhead code generator."""
    
    SYSTEM_PROMPT = """You are an expert Copperhead programmer. You have deep knowledge of Copperhead's type system, ownership model, and compilation pipeline.

## COPPERHEAD LANGUAGE REFERENCE

### Core Concept
Copperhead is a Python-like language that transpiles to Rust via PyO3. Code written in Copperhead:
1. Runs as normal Python (no compilation needed)
2. Can be compiled to Rust for 10-100x performance boost
3. Uses Python syntax with optional Rust type annotations

### Type System
```python
import copperhead as cp

# Primitive types (map directly to Rust)
x: cp.i8 = 127        # Rust i8
y: cp.i16 = 32767     # Rust i16  
z: cp.i32 = 2147483647 # Rust i32
w: cp.i64 = 9223372036854775807  # Rust i64

# Unsigned integers
a: cp.u8 = 255        # Rust u8
b: cp.u16 = 65535     # Rust u16
c: cp.u32 = 4294967295 # Rust u32
d: cp.u64 = 18446744073709551615  # Rust u64

# Size types
s1: cp.usize = 100    # Rust usize (platform-dependent)
s2: cp.isize = -100   # Rust isize

# Float types
f1: cp.f32 = 3.14     # Rust f32 (single precision)
f2: cp.f64 = 3.141592653589793  # Rust f64 (double precision)

# Other primitives
flag: cp.bool = True   # Rust bool
char: cp.char = "A"    # Rust char
text: cp.str = "Hello" # Rust String
data: cp.bytes = b"bin" # Rust Vec<u8>
```

### Collection Types
```python
# Dynamic arrays (Rust Vec)
vec: list[cp.f64] = [1.0, 2.0, 3.0]
matrix: list[list[cp.f64]] = [[1.0, 2.0], [3.0, 4.0]]

# Dictionaries (Rust HashMap)
map: dict[cp.str, cp.i32] = {"one": 1, "two": 2}

# Sets (Rust HashSet)
s: set[cp.i32] = {1, 2, 3}

# Tuples (Rust tuple)
pair: tuple[cp.f64, cp.i32] = (1.0, 42)
triple: tuple[cp.i32, cp.i32, cp.i32] = (1, 2, 3)

# Optional values (Rust Option)
opt: cp.Option[cp.f64] = cp.Option(42.0)
empty: cp.Option[cp.f64] = cp.Option()

# Result type (Rust Result)
ok: cp.Result[cp.f64] = cp.Ok(42.0)
err: cp.Result[cp.f64] = cp.Err("error message")
```

### Ownership and Borrowing
```python
# Mutable reference (Rust &mut T)
def mutate_state(state: cp.mut[State], value: cp.f64) -> None:
    state.counter += 1  # Can modify state
    state.data.append(value)

# Immutable reference (Rust &T)
def read_data(ref_data: cp.ref[Data]) -> cp.f64:
    total: cp.f64 = 0.0
    for val in ref_data.values:
        total += val  # Cannot modify ref_data
    return total

# Complex ownership example
def process_data(
    input_data: cp.ref[list[cp.f64]],  # Read-only input
    output: cp.mut[list[cp.f64]],       # Writable output
    config: cp.ref[Config]              # Read-only config
) -> cp.f64:
    for val in input_data:
        output.append(val * config.multiplier)
    return sum(output)
```

### Decorators
```python
# @cp.compile(target="rust") - Marks function for Rust compilation
@cp.compile(target="rust")
def compute(x: cp.f64) -> cp.f64:
    return x * x + cp.math.sin(x)

# @cp.no_gil - Releases GIL for true parallelism
@cp.compile(target="rust")
@cp.no_gil
def cpu_intensive(data: list[cp.f64]) -> cp.f64:
    total: cp.f64 = 0.0
    for val in data:
        total += cp.math.sin(val) * cp.math.cos(val)
    return total

# Combining both decorators
@cp.compile(target="rust")
@cp.no_gil
def parallel_process(items: list[cp.f64]) -> list[cp.f64]:
    result: list[cp.f64] = []
    for item in items:
        result.append(cp.math.sqrt(item))
    return result
```

### Math Module
```python
# Trigonometric functions
cp.math.sin(x)      # Sine
cp.math.cos(x)      # Cosine
cp.math.tan(x)      # Tangent

# Power and roots
cp.math.sqrt(x)     # Square root
cp.math.pow(x, y)   # x raised to power y

# Absolute value
cp.math.abs(x)      # Absolute value

# Rounding
cp.math.floor(x)    # Round down
cp.math.ceil(x)     # Round up

# Logarithmic
cp.math.log(x)      # Natural log
cp.math.log2(x)     # Log base 2
cp.math.log10(x)    # Log base 10

# Min/Max
cp.math.min(a, b)   # Minimum
cp.math.max(a, b)   # Maximum
```

### Error Handling Pattern
```python
@cp.compile(target="rust")
def safe_divide(a: cp.f64, b: cp.f64) -> cp.Result[cp.f64]:
    if b == 0.0:
        return cp.Err("Division by zero")
    return cp.Ok(a / b)

@cp.compile(target="rust")
def process_value(x: cp.Option[cp.f64]) -> cp.f64:
    return x.unwrap_or(0.0)
```

## CODE GENERATION RULES

1. **Always include imports**: Start with `import copperhead as cp`
2. **Always add type annotations**: Every variable and function parameter needs types
3. **Always use @cp.compile**: For any function that needs Rust performance
4. **Use @cp.no_gil for CPU-intensive work**: Loops, math operations, data processing
5. **Prefer typed collections**: Use `list[cp.f64]` not just `list`
6. **Handle errors explicitly**: Use cp.Result for operations that can fail
7. **Use ownership annotations**: When function needs to modify data, use cp.mut[T]

## TEST GENERATION RULES

1. Test normal cases with typical inputs
2. Test edge cases: empty collections, zero values, boundary values
3. Test error cases: invalid inputs, division by zero, out of bounds
4. Use pytest assertions: assert, pytest.raises for exceptions
5. Include docstrings explaining what each test verifies

## EXISTING MODULES IN REGISTRY

Before generating new code, check if similar functionality exists in the registry.
Available functions will be listed in the prompt.

## RESPONSE FORMAT

Respond in JSON format:
```json
{
    "ambiguities": [],
    "existing_modules": ["module1", "module2"],
    "reuse_functions": [
        {"module": "module_name", "function": "func_name", "usage": "how to use it"}
    ],
    "code": {
        "source": "Complete Copperhead source code with imports",
        "tests": "Complete pytest test file",
        "explanation": "What the code does and design decisions"
    },
    "questions": [],
    "debug_suggestions": ["Suggestion 1", "Suggestion 2"]
}
```

If ambiguities exist, put them in the ambiguities array and leave code empty.
If reusing existing functions, describe how in reuse_functions.
Always include debug_suggestions for potential issues."""

    def __init__(self, model: str = "maryasov/qwen2.5-coder-cline:latest"):
        self.client = OllamaClient(model)
        self.conversation_history: List[Dict[str, str]] = []
        self.registry = get_registry()
        self.debugger = CopperheadDebugger()
        self.validator = CodeValidator()
    
    def generate_from_description(
        self,
        description: str,
        existing_code: Optional[str] = None,
        max_iterations: int = 3,
        search_registry: bool = True
    ) -> GenerationResult:
        """Generate Copperhead code from a natural language description."""
        iteration = 0
        errors = []
        last_code = None
        used_modules = []
        
        # Search registry for existing modules
        existing_functions = []
        if search_registry:
            existing_functions = self._search_registry(description)
        
        while iteration < max_iterations:
            iteration += 1
            
            try:
                # Build the prompt with registry context
                prompt = self._build_prompt(
                    description, existing_code, last_code, 
                    iteration, existing_functions, used_modules
                )
                
                # Generate response
                response = self.client.generate(prompt, self.SYSTEM_PROMPT)
                
                # Parse response
                result = self._parse_response(response)
                
                if result is None:
                    errors.append(f"Iteration {iteration}: Failed to parse LLM response")
                    continue
                
                # Check for ambiguities that need resolution
                if result.get("questions") and len(result["questions"]) > 0:
                    if iteration == max_iterations:
                        # Return ambiguities for user to resolve
                        ambiguities = self._extract_ambiguities(result)
                        return GenerationResult(
                            success=False,
                            code=GeneratedCode(
                                source_code="",
                                tests_code="",
                                description=description,
                                ambiguities=ambiguities,
                                status=GenerationStatus.FAILED,
                                error_message="Ambiguities need resolution"
                            ),
                            iterations=iteration,
                            errors=errors
                        )
                    continue
                
                # Track used modules
                if result.get("existing_modules"):
                    used_modules.extend(result["existing_modules"])
                
                # Validate the generated code
                code_result = self._validate_code(result)
                code_result.used_modules = used_modules
                
                if code_result.status == GenerationStatus.SUCCESS:
                    # Run debugger
                    debug_result = self.debugger.debug(code_result.source_code)
                    code_result.debug_result = debug_result
                    
                    # If there are critical errors, try to fix
                    if debug_result.messages:
                        has_critical = any(
                            m.severity.value >= 4  # ERROR or CRITICAL
                            for m in debug_result.messages
                        )
                        if has_critical and iteration < max_iterations:
                            # Add debug info to errors for next iteration
                            debug_info = "\n".join([
                                f"[{m.severity.name}] {m.message}"
                                for m in debug_result.messages
                            ])
                            errors.append(f"Iteration {iteration} debug issues:\n{debug_info}")
                            last_code = code_result.source_code
                            continue
                    
                    return GenerationResult(
                        success=True,
                        code=code_result,
                        iterations=iteration,
                        errors=errors
                    )
                else:
                    errors.append(f"Iteration {iteration}: {code_result.error_message}")
                    last_code = code_result.source_code
            
            except Exception as e:
                errors.append(f"Iteration {iteration}: {str(e)}")
        
        return GenerationResult(
            success=False,
            iterations=iteration,
            errors=errors
        )
    
    def _search_registry(self, description: str) -> List[Tuple[ModuleMetadata, FunctionSignature]]:
        """Search registry for relevant existing functions."""
        # Extract keywords from description
        keywords = description.lower().split()
        
        # Search for matching functions
        results = []
        for keyword in keywords:
            if len(keyword) > 3:  # Skip short words
                matches = self.registry.search_functions(keyword, limit=5)
                results.extend(matches)
        
        # Deduplicate
        seen = set()
        unique_results = []
        for module, func in results:
            key = f"{module.id}:{func.name}"
            if key not in seen:
                seen.add(key)
                unique_results.append((module, func))
        
        return unique_results[:10]  # Limit to 10 results
    
    def _build_prompt(
        self,
        description: str,
        existing_code: Optional[str],
        last_code: Optional[str],
        iteration: int,
        existing_functions: Optional[List[Tuple[ModuleMetadata, FunctionSignature]]] = None,
        used_modules: Optional[List[str]] = None
    ) -> str:
        """Build the prompt for the LLM."""
        parts = [f"User description: {description}"]
        
        # Add existing functions from registry
        if existing_functions:
            parts.append("\n## EXISTING FUNCTIONS IN REGISTRY")
            parts.append("Consider reusing these functions instead of rewriting:")
            for module, func in existing_functions[:5]:
                args_str = ", ".join([f"{name}: {type_}" for name, type_ in func.args])
                parts.append(f"- {module.name}.{func.name}({args_str}) -> {func.return_type}")
                if func.description:
                    parts.append(f"  Description: {func.description}")
        
        # Add used modules
        if used_modules:
            parts.append(f"\nModules being reused: {', '.join(used_modules)}")
        
        if existing_code:
            parts.append(f"\nExisting code to modify:\n```python\n{existing_code}\n```")
        
        if last_code:
            parts.append(f"\nPrevious attempt that had issues:\n```python\n{last_code}\n```")
            parts.append("\nPlease fix the issues and generate corrected code.")
        
        if iteration > 1:
            parts.append(f"\nThis is iteration {iteration}. Please be more careful with the implementation.")
        
        parts.append("\nPlease generate complete Copperhead code and tests.")
        
        return "\n".join(parts)
    
    def _parse_response(self, response: str) -> Optional[Dict]:
        """Parse the LLM response into structured data."""
        try:
            # Try to extract JSON from response
            # Look for JSON block
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Try to parse entire response as JSON
            # First, find the first { and last }
            start = response.find('{')
            end = response.rfind('}')
            
            if start != -1 and end != -1:
                json_str = response[start:end + 1]
                return json.loads(json_str)
            
            # If no JSON found, create a simple structure
            return {
                "ambiguities": [],
                "code": {
                    "source": response,
                    "tests": "",
                    "explanation": ""
                },
                "questions": []
            }
        
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract code blocks
            code_match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
            if code_match:
                return {
                    "ambiguities": [],
                    "code": {
                        "source": code_match.group(1),
                        "tests": "",
                        "explanation": response
                    },
                    "questions": []
                }
            
            return None
    
    def _extract_ambiguities(self, result: Dict) -> List[Ambiguity]:
        """Extract ambiguities from the parsed result."""
        ambiguities = []
        
        for amb in result.get("ambiguities", []):
            ambiguities.append(Ambiguity(
                question=amb.get("question", ""),
                context=amb.get("context", ""),
                options=amb.get("options", []),
                recommendation=amb.get("recommendation", "")
            ))
        
        return ambiguities
    
    def _validate_code(self, result: Dict) -> GeneratedCode:
        """Validate the generated code."""
        code_data = result.get("code", {})
        
        source_code = code_data.get("source", "")
        tests_code = code_data.get("tests", "")
        explanation = code_data.get("explanation", "")
        
        # Validate Python syntax
        try:
            ast.parse(source_code)
        except SyntaxError as e:
            return GeneratedCode(
                source_code=source_code,
                tests_code=tests_code,
                description=explanation,
                status=GenerationStatus.FAILED,
                error_message=f"Syntax error in generated code: {e}"
            )
        
        # Validate test syntax if provided
        if tests_code:
            try:
                ast.parse(tests_code)
            except SyntaxError as e:
                return GeneratedCode(
                    source_code=source_code,
                    tests_code=tests_code,
                    description=explanation,
                    status=GenerationStatus.FAILED,
                    error_message=f"Syntax error in generated tests: {e}"
                )
        
        # Check for required Copperhead patterns
        if "@cp.compile" not in source_code and "import copperhead" not in source_code:
            # Might not be Copperhead code, but that's okay
            pass
        
        return GeneratedCode(
            source_code=source_code,
            tests_code=tests_code,
            description=explanation,
            status=GenerationStatus.SUCCESS
        )
    
    def refine_code(
        self,
        code: GeneratedCode,
        error_message: str,
        user_feedback: Optional[str] = None
    ) -> GenerationResult:
        """Refine existing code based on errors or feedback."""
        prompt = f"""The following Copperhead code has issues:

Source code:
```python
{code.source_code}
```

Tests:
```python
{code.tests_code}
```

Error: {error_message}

"""
        
        if user_feedback:
            prompt += f"User feedback: {user_feedback}\n\n"
        
        prompt += "Please fix the issues and provide corrected code."
        
        return self.generate_from_description(prompt, max_iterations=2)
    
    def explain_code(self, code: str) -> str:
        """Explain what the code does."""
        prompt = f"""Please explain what the following Copperhead code does:

```python
{code}
```

Provide a clear, concise explanation suitable for documentation."""
        
        return self.client.generate(prompt, self.SYSTEM_PROMPT)
    
    def suggest_improvements(self, code: str) -> str:
        """Suggest improvements to the code."""
        prompt = f"""Please analyze the following Copperhead code and suggest improvements:

```python
{code}
```

Consider:
1. Performance optimizations
2. Better type annotations
3. Error handling improvements
4. Code organization
5. Idiomatic Copperhead usage"""
        
        return self.client.generate(prompt, self.SYSTEM_PROMPT)


class CodeGenerator:
    """High-level code generation interface."""
    
    def __init__(self, model: str = "maryasov/qwen2.5-coder-cline:latest"):
        self.coder = CopperheadCoder(model)
        self.output_dir = "generated"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate(
        self,
        description: str,
        output_name: str = "generated_module",
        auto_test: bool = True,
        max_iterations: int = 3
    ) -> GenerationResult:
        """Generate code from description and save to files."""
        # Check Ollama availability
        if not self.coder.client.is_available():
            return GenerationResult(
                success=False,
                errors=["Ollama is not available. Please install and start Ollama."]
            )
        
        # Generate code
        result = self.coder.generate_from_description(
            description,
            max_iterations=max_iterations
        )
        
        if result.success and result.code:
            # Save source code
            source_path = os.path.join(self.output_dir, f"{output_name}.py")
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write(result.code.source_code)
            
            # Save tests
            if result.code.tests_code:
                tests_path = os.path.join(self.output_dir, f"test_{output_name}.py")
                with open(tests_path, 'w', encoding='utf-8') as f:
                    f.write(result.code.tests_code)
            
            # Run tests if auto_test is enabled
            if auto_test and result.code.tests_code:
                test_result = self._run_tests(tests_path)
                if not test_result["success"]:
                    # Try to fix the code
                    refine_result = self.coder.refine_code(
                        result.code,
                        test_result["error"],
                        "Tests failed, please fix the code"
                    )
                    if refine_result.success and refine_result.code:
                        # Update files with refined code
                        with open(source_path, 'w', encoding='utf-8') as f:
                            f.write(refine_result.code.source_code)
                        if refine_result.code.tests_code:
                            with open(tests_path, 'w', encoding='utf-8') as f:
                                f.write(refine_result.code.tests_code)
                        result = refine_result
        
        return result
    
    def _run_tests(self, test_path: str) -> Dict[str, Any]:
        """Run tests and return results."""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", test_path, "-v"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Tests timed out (60s limit)"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }
    
    def interact(self):
        """Interactive mode for code generation."""
        print("Copperhead Code Generator (Interactive Mode)")
        print("=" * 50)
        print("Describe what you want to create, and I'll generate Copperhead code.")
        print("Type 'quit' to exit, 'help' for commands.\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() == 'quit':
                    print("Goodbye!")
                    break
                
                if user_input.lower() == 'help':
                    self._print_help()
                    continue
                
                if not user_input:
                    continue
                
                print("\nGenerating code...")
                result = self.generate(user_input)
                
                if result.success and result.code:
                    print("\nGenerated Code:")
                    print("-" * 50)
                    print(result.code.source_code)
                    
                    if result.code.tests_code:
                        print("\nGenerated Tests:")
                        print("-" * 50)
                        print(result.code.tests_code)
                    
                    if result.code.description:
                        print("\nExplanation:")
                        print("-" * 50)
                        print(result.code.description)
                    
                    print(f"\nCompleted in {result.iterations} iteration(s)")
                
                elif result.code and result.code.ambiguities:
                    print("\nI need some clarifications:")
                    for amb in result.code.ambiguities:
                        print(f"\n{amb.question}")
                        print(f"Context: {amb.context}")
                        for i, opt in enumerate(amb.options, 1):
                            print(f"  {i}. {opt}")
                        print(f"Recommendation: {amb.recommendation}")
                
                else:
                    print("\nFailed to generate code:")
                    for error in result.errors:
                        print(f"  - {error}")
                
                print()
            
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")
    
    def _print_help(self):
        """Print help information."""
        print("""
Available commands:
  help     - Show this help message
  quit     - Exit the interactive mode

Examples of descriptions:
  "Create a function that calculates the factorial of a number"
  "Write a matrix multiplication function with error handling"
  "Create a function that finds all prime numbers up to n"
  "Write a function that sorts a list using quicksort"
  "Create a simple HTTP server that serves static files"

Tips:
  - Be specific about input/output types
  - Mention edge cases you want handled
  - Specify if you need error handling
  - Mention performance requirements (use @cp.no_gil for CPU-intensive)
""")


def generate_code(
    description: str,
    output_name: str = "generated_module",
    model: str = "maryasov/qwen2.5-coder-cline:latest"
) -> GenerationResult:
    """Convenience function to generate code from description."""
    generator = CodeGenerator(model)
    return generator.generate(description, output_name)


def interactive_mode(model: str = "maryasov/qwen2.5-coder-cline:latest"):
    """Start interactive code generation mode."""
    generator = CodeGenerator(model)
    generator.interact()
