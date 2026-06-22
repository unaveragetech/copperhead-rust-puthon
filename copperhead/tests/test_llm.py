"""
Tests for Copperhead LLM integration.
"""

import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copperhead.llm import (
    OllamaClient, CopperheadCoder, CodeGenerator,
    GenerationStatus, AmbiguityLevel, GeneratedCode,
    Ambiguity, GenerationResult
)


class TestOllamaClient:
    """Test OllamaClient class."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = OllamaClient()
        assert client.model == "maryasov/qwen2.5-coder-cline:latest"
        assert client.base_url == "http://localhost:11434"
    
    def test_client_custom_model(self):
        """Test client with custom model."""
        client = OllamaClient(model="custom-model")
        assert client.model == "custom-model"
    
    def test_is_available(self):
        """Test Ollama availability check."""
        client = OllamaClient()
        # This will return True if Ollama is running, False otherwise
        result = client.is_available()
        assert isinstance(result, bool)


class TestCopperheadCoder:
    """Test CopperheadCoder class."""
    
    def test_coder_initialization(self):
        """Test coder initialization."""
        coder = CopperheadCoder()
        assert coder.client is not None
        assert coder.conversation_history == []
    
    def test_coder_custom_model(self):
        """Test coder with custom model."""
        coder = CopperheadCoder(model="custom-model")
        assert coder.client.model == "custom-model"
    
    def test_build_prompt(self):
        """Test prompt building."""
        coder = CopperheadCoder()
        prompt = coder._build_prompt(
            description="Create a function to add two numbers",
            existing_code=None,
            last_code=None,
            iteration=1
        )
        assert "Create a function to add two numbers" in prompt
        assert "User description:" in prompt
    
    def test_build_prompt_with_existing_code(self):
        """Test prompt building with existing code."""
        coder = CopperheadCoder()
        existing = "def old_func(): pass"
        prompt = coder._build_prompt(
            description="Update this function",
            existing_code=existing,
            last_code=None,
            iteration=1
        )
        assert existing in prompt
        assert "Existing code to modify:" in prompt
    
    def test_build_prompt_with_last_code(self):
        """Test prompt building with last code attempt."""
        coder = CopperheadCoder()
        last_code = "def buggy_func(): pass"
        prompt = coder._build_prompt(
            description="Fix this function",
            existing_code=None,
            last_code=last_code,
            iteration=2
        )
        assert last_code in prompt
        assert "Previous attempt that had issues:" in prompt
        assert "iteration 2" in prompt
    
    def test_parse_response_valid_json(self):
        """Test parsing valid JSON response."""
        coder = CopperheadCoder()
        response = '''
        {
            "ambiguities": [],
            "code": {
                "source": "import copperhead as cp\\n\\n@cp.compile(target=\\"rust\\")\\ndef add(x: cp.f64, y: cp.f64) -> cp.f64:\\n    return x + y",
                "tests": "def test_add():\\n    assert add(1.0, 2.0) == 3.0",
                "explanation": "Simple add function"
            },
            "questions": []
        }
        '''
        result = coder._parse_response(response)
        assert result is not None
        assert "code" in result
        assert "source" in result["code"]
    
    def test_parse_response_json_in_code_block(self):
        """Test parsing JSON in code block."""
        coder = CopperheadCoder()
        response = '''
        Here's the code:
        
        ```json
        {
            "ambiguities": [],
            "code": {
                "source": "def func(): pass",
                "tests": "",
                "explanation": "Test"
            },
            "questions": []
        }
        ```
        '''
        result = coder._parse_response(response)
        assert result is not None
    
    def test_parse_response_code_only(self):
        """Test parsing response with only code."""
        coder = CopperheadCoder()
        response = '''
        ```python
        import copperhead as cp
        
        @cp.compile(target="rust")
        def add(x: cp.f64, y: cp.f64) -> cp.f64:
            return x + y
        ```
        '''
        result = coder._parse_response(response)
        assert result is not None
        assert "code" in result
    
    def test_parse_response_invalid(self):
        """Test parsing invalid response."""
        coder = CopperheadCoder()
        response = "This is not valid JSON or code"
        result = coder._parse_response(response)
        # Should return a basic structure
        assert result is not None
    
    def test_extract_ambiguities(self):
        """Test ambiguity extraction."""
        coder = CopperheadCoder()
        result = {
            "ambiguities": [
                {
                    "question": "What type of data?",
                    "context": "Data type not specified",
                    "options": ["integers", "floats"],
                    "recommendation": "floats"
                }
            ],
            "code": {"source": "", "tests": "", "explanation": ""},
            "questions": ["What type of data?"]
        }
        ambiguities = coder._extract_ambiguities(result)
        assert len(ambiguities) == 1
        assert ambiguities[0].question == "What type of data?"
        assert len(ambiguities[0].options) == 2
    
    def test_validate_code_valid(self):
        """Test code validation with valid code."""
        coder = CopperheadCoder()
        result = {
            "code": {
                "source": "def func(): pass",
                "tests": "def test_func(): pass",
                "explanation": "Test"
            }
        }
        validated = coder._validate_code(result)
        assert validated.status == GenerationStatus.SUCCESS
    
    def test_validate_code_syntax_error(self):
        """Test code validation with syntax error."""
        coder = CopperheadCoder()
        result = {
            "code": {
                "source": "def func(: pass",
                "tests": "",
                "explanation": "Test"
            }
        }
        validated = coder._validate_code(result)
        assert validated.status == GenerationStatus.FAILED
        assert "Syntax error" in validated.error_message
    
    def test_validate_code_test_syntax_error(self):
        """Test code validation with test syntax error."""
        coder = CopperheadCoder()
        result = {
            "code": {
                "source": "def func(): pass",
                "tests": "def test_func(: pass",
                "explanation": "Test"
            }
        }
        validated = coder._validate_code(result)
        assert validated.status == GenerationStatus.FAILED
        assert "Syntax error in generated tests" in validated.error_message


class TestCodeGenerator:
    """Test CodeGenerator class."""
    
    def test_generator_initialization(self):
        """Test generator initialization."""
        generator = CodeGenerator()
        assert generator.coder is not None
        assert generator.output_dir == "generated"
    
    def test_generator_custom_model(self):
        """Test generator with custom model."""
        generator = CodeGenerator(model="custom-model")
        assert generator.coder.client.model == "custom-model"
    
    def test_generator_creates_output_dir(self):
        """Test that generator creates output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = os.getcwd()
            os.chdir(tmpdir)
            try:
                generator = CodeGenerator()
                assert os.path.exists("generated")
            finally:
                os.chdir(old_dir)


class TestGeneratedCode:
    """Test GeneratedCode dataclass."""
    
    def test_generated_code_creation(self):
        """Test GeneratedCode creation."""
        code = GeneratedCode(
            source_code="def func(): pass",
            tests_code="def test_func(): pass",
            description="Test function"
        )
        assert code.source_code == "def func(): pass"
        assert code.tests_code == "def test_func(): pass"
        assert code.status == GenerationStatus.PENDING
        assert code.ambiguities == []
    
    def test_generated_code_with_ambiguities(self):
        """Test GeneratedCode with ambiguities."""
        amb = Ambiguity(
            question="What type?",
            context="Not specified",
            options=["int", "float"],
            recommendation="float"
        )
        code = GeneratedCode(
            source_code="",
            tests_code="",
            description="",
            ambiguities=[amb]
        )
        assert len(code.ambiguities) == 1


class TestGenerationResult:
    """Test GenerationResult dataclass."""
    
    def test_generation_result_success(self):
        """Test successful GenerationResult."""
        code = GeneratedCode(
            source_code="def func(): pass",
            tests_code="",
            description="Test"
        )
        result = GenerationResult(
            success=True,
            code=code,
            iterations=1
        )
        assert result.success is True
        assert result.code is not None
        assert result.iterations == 1
    
    def test_generation_result_failure(self):
        """Test failed GenerationResult."""
        result = GenerationResult(
            success=False,
            errors=["Failed to generate"]
        )
        assert result.success is False
        assert len(result.errors) == 1


class TestAmbiguity:
    """Test Ambiguity dataclass."""
    
    def test_ambiguity_creation(self):
        """Test Ambiguity creation."""
        amb = Ambiguity(
            question="What size?",
            context="Size not specified",
            options=["small", "medium", "large"],
            recommendation="medium"
        )
        assert amb.question == "What size?"
        assert len(amb.options) == 3
        assert amb.recommendation == "medium"


class TestEnums:
    """Test enum classes."""
    
    def test_generation_status(self):
        """Test GenerationStatus enum."""
        assert GenerationStatus.PENDING.value == 1
        assert GenerationStatus.GENERATING.value == 2
        assert GenerationStatus.VALIDATING.value == 3
        assert GenerationStatus.REFINDING.value == 4
        assert GenerationStatus.SUCCESS.value == 5
        assert GenerationStatus.FAILED.value == 6
    
    def test_ambiguity_level(self):
        """Test AmbiguityLevel enum."""
        assert AmbiguityLevel.NONE.value == 1
        assert AmbiguityLevel.LOW.value == 2
        assert AmbiguityLevel.MEDIUM.value == 3
        assert AmbiguityLevel.HIGH.value == 4
