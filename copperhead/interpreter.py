"""
Copperhead Interactive Interpreter

A shared workspace where users and the LLM agent can write, edit, and debug code together.
The interpreter supports:
- Natural language commands
- Code editing with line numbers
- Real-time debugging
- Session history
- Collaborative editing between user and LLM
"""

import os
import sys
import json
import time
import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum, auto


class CommandType(Enum):
    """Types of commands the interpreter can handle."""
    CODE = auto()        # Direct code input
    NL_COMMAND = auto()  # Natural language command
    DEBUG = auto()       # Debug command
    BUILD = auto()       # Build/compile command
    TEST = auto()        # Test command
    HELP = auto()        # Help command
    EXIT = auto()        # Exit command
    UNDO = auto()        # Undo command
    REDO = auto()        # Redo command
    HISTORY = auto()     # History command
    SAVE = auto()        # Save command
    LOAD = auto()        # Load command
    LIST = auto()        # List code command
    CLEAR = auto()       # Clear command
    AGENT = auto()       # Agent command (ask LLM for help)


@dataclass
class CodeBlock:
    """A block of code in the workspace."""
    id: str
    name: str
    content: str
    line_start: int
    line_end: int
    language: str = "python"
    description: str = ""
    author: str = "user"  # "user" or "agent"
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    is_rpb: bool = False
    is_test: bool = False


@dataclass
class SessionState:
    """Current state of the interpreter session."""
    blocks: List[CodeBlock] = field(default_factory=list)
    history: List[str] = field(default_factory=list)
    undo_stack: List[List[CodeBlock]] = field(default_factory=list)
    redo_stack: List[List[CodeBlock]] = field(default_factory=list)
    current_file: Optional[str] = None
    modified: bool = False
    agent_enabled: bool = True
    
    def save_state(self) -> None:
        """Save current state to undo stack."""
        import copy
        self.undo_stack.append(copy.deepcopy(self.blocks))
        self.redo_stack.clear()
    
    def undo(self) -> bool:
        """Undo last change."""
        if not self.undo_stack:
            return False
        import copy
        self.redo_stack.append(copy.deepcopy(self.blocks))
        self.blocks = self.undo_stack.pop()
        return True
    
    def redo(self) -> bool:
        """Redo last undone change."""
        if not self.redo_stack:
            return False
        import copy
        self.undo_stack.append(copy.deepcopy(self.blocks))
        self.blocks = self.redo_stack.pop()
        return True


class CopperheadInterpreter:
    """Interactive interpreter for Copperhead code development."""
    
    def __init__(self, use_agent: bool = True):
        self.state = SessionState(agent_enabled=use_agent)
        self.commands: Dict[str, Callable] = {}
        self._register_commands()
        
        # Import components
        try:
            from .llm import CopperheadCoder
            self.agent = CopperheadCoder() if use_agent else None
        except Exception:
            self.agent = None
            self.state.agent_enabled = False
        
        try:
            from .debugger import CopperheadDebugger
            self.debugger = CopperheadDebugger()
        except Exception:
            self.debugger = None
        
        try:
            from .registry import get_registry
            self.registry = get_registry()
        except Exception:
            self.registry = None
    
    def _register_commands(self) -> None:
        """Register built-in commands."""
        self.commands = {
            "help": self._cmd_help,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
            "list": self._cmd_list,
            "show": self._cmd_list,
            "clear": self._cmd_clear,
            "undo": self._cmd_undo,
            "redo": self._cmd_redo,
            "history": self._cmd_history,
            "save": self._cmd_save,
            "load": self._cmd_load,
            "debug": self._cmd_debug,
            "test": self._cmd_test,
            "build": self._cmd_build,
            "run": self._cmd_run,
            "agent": self._cmd_agent,
            "registry": self._cmd_registry,
        }
    
    def parse_input(self, user_input: str) -> Tuple[CommandType, str, Dict[str, Any]]:
        """Parse user input into command type and arguments."""
        stripped = user_input.strip()
        
        # Check for command prefix
        if stripped.startswith(":"):
            parts = stripped[1:].split(None, 1)
            cmd = parts[0].lower() if parts else ""
            args = parts[1] if len(parts) > 1 else ""
            
            if cmd in self.commands:
                return (CommandType.NL_COMMAND, cmd, {"args": args})
            elif cmd == "agent":
                return (CommandType.AGENT, args, {})
            elif cmd == "debug":
                return (CommandType.DEBUG, args, {})
            elif cmd == "build":
                return (CommandType.BUILD, args, {})
            elif cmd == "test":
                return (CommandType.TEST, args, {})
        
        # Check for special prefixes
        if stripped.startswith("?"):
            return (CommandType.AGENT, stripped[1:], {})
        
        if stripped.startswith("!"):
            return (CommandType.CODE, stripped[1:], {"execute": True})
        
        # Check if it looks like code
        if self._looks_like_code(stripped):
            return (CommandType.CODE, stripped, {})
        
        # Default: treat as natural language for the agent
        return (CommandType.NL_COMMAND, "describe", {"description": stripped})
    
    def _looks_like_code(self, text: str) -> bool:
        """Heuristic to determine if text looks like code."""
        code_indicators = [
            "def ", "class ", "import ", "from ", "if ", "for ", "while ",
            "return ", "yield ", "raise ", "try:", "except:", "finally:",
            "=", "==", "!=", "<=", ">=", "+=", "-=", "*=", "/=",
            "(", ")", "[", "]", "{", "}", ":", ";"
        ]
        
        lines = text.split("\n")
        code_lines = sum(1 for line in lines 
                        if any(indicator in line for indicator in code_indicators))
        
        return code_lines > len(lines) * 0.3
    
    def process_input(self, user_input: str) -> Tuple[bool, str]:
        """Process user input and return (should_continue, response)."""
        cmd_type, content, kwargs = self.parse_input(user_input)
        
        if cmd_type == CommandType.CODE:
            return self._handle_code(content, **kwargs)
        elif cmd_type == CommandType.NL_COMMAND:
            return self._handle_nl_command(content, **kwargs)
        elif cmd_type == CommandType.AGENT:
            return self._handle_agent(content)
        elif cmd_type == CommandType.DEBUG:
            return self._handle_debug(content)
        elif cmd_type == CommandType.BUILD:
            return self._handle_build(content)
        elif cmd_type == CommandType.TEST:
            return self._handle_test(content)
        elif cmd_type == CommandType.EXIT:
            return self._cmd_exit("")
        
        return True, "Unknown command. Type :help for available commands."
    
    def _handle_code(self, code: str, execute: bool = False) -> Tuple[bool, str]:
        """Handle code input."""
        # Add to workspace
        block_id = f"block_{len(self.state.blocks)}"
        lines = code.split("\n")
        
        block = CodeBlock(
            id=block_id,
            name=f"block_{len(self.state.blocks)}",
            content=code,
            line_start=1,
            line_end=len(lines),
            description="User input",
            author="user"
        )
        
        self.state.save_state()
        self.state.blocks.append(block)
        self.state.history.append(f"Added code block {block_id}")
        
        response = f"Added code block ({len(lines)} lines)"
        
        if execute:
            # Execute the code
            try:
                exec(code, {"__builtins__": __builtins__})
                response += "\nCode executed successfully."
            except Exception as e:
                response += f"\nExecution error: {e}"
        
        return True, response
    
    def _handle_nl_command(self, command: str, **kwargs) -> Tuple[bool, str]:
        """Handle natural language command."""
        if command in self.commands:
            return self.commands[command](kwargs.get("args", ""))
        
        description = kwargs.get("description", command)
        
        if not self.state.agent_enabled or not self.agent:
            return True, "Agent is not enabled. Use code blocks or commands."
        
        # Ask agent to generate code
        print("Thinking...")
        result = self.agent.generate_from_description(
            description,
            max_iterations=2,
            search_registry=True
        )
        
        if result.success and result.code:
            # Add generated code
            block_id = f"agent_{len(self.state.blocks)}"
            block = CodeBlock(
                id=block_id,
                name=f"agent_{len(self.state.blocks)}",
                content=result.code.source_code,
                line_start=1,
                line_end=len(result.code.source_code.split("\n")),
                description=description,
                author="agent"
            )
            
            self.state.save_state()
            self.state.blocks.append(block)
            
            # Add tests if available
            if result.code.tests_code:
                test_block = CodeBlock(
                    id=f"{block_id}_test",
                    name=f"test_{block_id}",
                    content=result.code.tests_code,
                    line_start=1,
                    line_end=len(result.code.tests_code.split("\n")),
                    description=f"Tests for {description}",
                    author="agent",
                    is_test=True
                )
                self.state.blocks.append(test_block)
            
            response = f"Agent generated code:\n\n{result.code.source_code}"
            if result.code.tests_code:
                response += f"\n\nTests:\n\n{result.code.tests_code}"
            if result.code.description:
                response += f"\n\nExplanation: {result.code.description}"
            
            return True, response
        
        elif result.code and result.code.ambiguities:
            response = "I need some clarifications:\n"
            for amb in result.code.ambiguities:
                response += f"\n{amb.question}"
                response += f"\nContext: {amb.context}"
                for i, opt in enumerate(amb.options, 1):
                    response += f"\n  {i}. {opt}"
                response += f"\nRecommendation: {amb.recommendation}"
            return True, response
        
        else:
            response = "Failed to generate code:\n"
            for error in result.errors:
                response += f"  - {error}\n"
            return True, response
    
    def _handle_agent(self, query: str) -> Tuple[bool, str]:
        """Handle agent query."""
        if not self.agent:
            return True, "Agent is not available."
        
        print("Agent thinking...")
        
        # Build context from current workspace
        context = self.get_workspace_content()
        
        if context:
            query = f"Current workspace:\n```\n{context}\n```\n\n{query}"
        
        result = self.agent.generate_from_description(
            query,
            max_iterations=2
        )
        
        if result.success and result.code:
            return True, f"Agent response:\n\n{result.code.source_code}"
        else:
            return True, "Agent could not generate a response."
    
    def _handle_debug(self, target: str) -> Tuple[bool, str]:
        """Handle debug command."""
        if not self.debugger:
            return True, "Debugger is not available."
        
        # Debug the entire workspace
        content = self.get_workspace_content()
        if not content:
            return True, "No code to debug."
        
        result = self.debugger.debug(content)
        
        response = "Debug results:\n"
        if result.messages:
            for msg in result.messages:
                response += f"\n[{msg.severity.name}] {msg.message}"
                if msg.line:
                    response += f" (line {msg.line})"
                if msg.suggestion:
                    response += f"\n  Suggestion: {msg.suggestion}"
        else:
            response += "\nNo issues found."
        
        return True, response
    
    def _handle_test(self, target: str) -> Tuple[bool, str]:
        """Handle test command."""
        # Find test blocks
        test_blocks = [b for b in self.state.blocks if b.is_test]
        
        if not test_blocks:
            return True, "No test blocks found."
        
        import tempfile
        import subprocess
        
        # Combine all tests
        all_tests = "\n\n".join([b.content for b in test_blocks])
        
        # Write to temp file and run
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(all_tests)
            temp_path = f.name
        
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", temp_path, "-v"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, f"Tests passed:\n{result.stdout}"
            else:
                return True, f"Tests failed:\n{result.stdout}\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return True, "Tests timed out."
        except Exception as e:
            return True, f"Error running tests: {e}"
        finally:
            os.unlink(temp_path)
    
    def _handle_build(self, target: str) -> Tuple[bool, str]:
        """Handle build command."""
        content = self.get_workspace_content()
        if not content:
            return True, "No code to build."
        
        # Save to temp file
        import tempfile
        from .compiler import BuildConfig, CopperheadCompiler, CompilationStatus
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            config = BuildConfig(source_path=temp_path, use_cache=False)
            compiler = CopperheadCompiler(config)
            result = compiler.compile()
            
            if result.status == CompilationStatus.SUCCESS:
                return True, "Build successful!"
            else:
                return True, f"Build failed: {result.error_message}"
        except Exception as e:
            return True, f"Build error: {e}"
        finally:
            os.unlink(temp_path)
    
    def _cmd_help(self, args: str) -> Tuple[bool, str]:
        """Show help message."""
        help_text = """
Copperhead Interpreter Commands:
================================

Code Operations:
  <code>              Add code to workspace
  !<code>             Add and execute code
  :list               Show all code blocks
  :clear              Clear workspace

Agent Commands:
  ?<description>      Ask agent to generate code
  :agent <query>      Ask agent for help
  :debug              Debug current code
  :test               Run tests
  :build              Build/compile code

Session Commands:
  :undo               Undo last change
  :redo               Redo last undone change
  :history            Show command history
  :save <filename>    Save workspace to file
  :load <filename>    Load workspace from file

Registry Commands:
  :registry list      List registered modules
  :registry search <q> Search modules

General:
  :help               Show this help message
  :exit               Exit interpreter

Natural Language:
  You can also just type a description and the agent
  will generate code for you.

Examples:
  ?Create a function that sorts a list using quicksort
  def add(x: float, y: float) -> float: return x + y
  :debug
  :test
"""
        return True, help_text
    
    def _cmd_exit(self, args: str) -> Tuple[bool, str]:
        """Exit the interpreter."""
        if self.state.modified:
            return False, "Session modified. Use :exit again to force quit."
        return False, "Goodbye!"
    
    def _cmd_list(self, args: str) -> Tuple[bool, str]:
        """List all code blocks."""
        if not self.state.blocks:
            return True, "No code blocks in workspace."
        
        response = "Workspace blocks:\n"
        for i, block in enumerate(self.state.blocks):
            author = "[AGENT]" if block.author == "agent" else "[USER]"
            test = "[TEST]" if block.is_test else ""
            lines = len(block.content.split("\n"))
            response += f"\n{i+1}. {block.name} ({lines} lines) {author} {test}"
            if block.description:
                response += f" - {block.description}"
        
        return True, response
    
    def _cmd_clear(self, args: str) -> Tuple[bool, str]:
        """Clear workspace."""
        self.state.save_state()
        self.state.blocks.clear()
        return True, "Workspace cleared."
    
    def _cmd_undo(self, args: str) -> Tuple[bool, str]:
        """Undo last change."""
        if self.state.undo():
            return True, "Undone."
        return True, "Nothing to undo."
    
    def _cmd_redo(self, args: str) -> Tuple[bool, str]:
        """Redo last undone change."""
        if self.state.redo():
            return True, "Redone."
        return True, "Nothing to redo."
    
    def _cmd_history(self, args: str) -> Tuple[bool, str]:
        """Show command history."""
        if not self.state.history:
            return True, "No history."
        
        response = "History:\n"
        for i, entry in enumerate(self.state.history[-20:], 1):
            response += f"\n{i}. {entry}"
        
        return True, response
    
    def _cmd_save(self, args: str) -> Tuple[bool, str]:
        """Save workspace to file."""
        if not args:
            return True, "Usage: :save <filename>"
        
        filename = args.strip()
        content = self.get_workspace_content()
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            self.state.current_file = filename
            self.state.modified = False
            return True, f"Saved to {filename}"
        except Exception as e:
            return True, f"Error saving: {e}"
    
    def _cmd_load(self, args: str) -> Tuple[bool, str]:
        """Load workspace from file."""
        if not args:
            return True, "Usage: :load <filename>"
        
        filename = args.strip()
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.state.save_state()
            self.state.blocks.clear()
            
            block = CodeBlock(
                id="loaded",
                name=os.path.basename(filename),
                content=content,
                line_start=1,
                line_end=len(content.split("\n")),
                description=f"Loaded from {filename}",
                author="user"
            )
            self.state.blocks.append(block)
            self.state.current_file = filename
            
            return True, f"Loaded {filename}"
        except Exception as e:
            return True, f"Error loading: {e}"
    
    def _cmd_registry(self, args: str) -> Tuple[bool, str]:
        """Registry commands."""
        if not self.registry:
            return True, "Registry not available."
        
        parts = args.split(None, 1)
        action = parts[0] if parts else "list"
        target = parts[1] if len(parts) > 1 else ""
        
        if action == "list":
            modules = self.registry.get_all_modules()
            if not modules:
                return True, "No modules registered."
            
            response = "Registered modules:\n"
            for m in modules:
                response += f"\n  {m.name} (v{m.version}) - {len(m.functions)} functions"
            return True, response
        
        elif action == "search":
            if not target:
                return True, "Usage: :registry search <query>"
            
            modules = self.registry.search_modules(target)
            if not modules:
                return True, "No modules found."
            
            response = f"Search results for '{target}':\n"
            for m in modules:
                response += f"\n  {m.name} - {m.description}"
            return True, response
        
        return True, "Usage: :registry [list|search] [query]"
    
    def get_workspace_content(self) -> str:
        """Get all code blocks as a single string."""
        if not self.state.blocks:
            return ""
        
        parts = []
        for block in self.state.blocks:
            parts.append(f"# === {block.name} ===\n{block.content}")
        
        return "\n\n".join(parts)
    
    def run_interactive(self) -> None:
        """Run the interactive interpreter."""
        print("\n" + "=" * 60)
        print(" Copperhead Interactive Interpreter")
        print("=" * 60)
        print("\nType :help for available commands")
        print("Type ?<description> to generate code with AI")
        print("Or just describe what you want to create\n")
        
        while True:
            try:
                # Show prompt
                prompt = "copperhead> "
                user_input = input(prompt)
                
                if not user_input.strip():
                    continue
                
                # Process input
                should_continue, response = self.process_input(user_input)
                
                if response:
                    print(f"\n{response}\n")
                
                if not should_continue:
                    break
                
                self.state.modified = True
            
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type :exit to quit.")
            except EOFError:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}\n")


def start_interpreter(use_agent: bool = True) -> None:
    """Start the Copperhead interpreter."""
    interpreter = CopperheadInterpreter(use_agent=use_agent)
    interpreter.run_interactive()


if __name__ == "__main__":
    start_interpreter()
