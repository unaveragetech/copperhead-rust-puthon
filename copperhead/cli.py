"""
Copperhead CLI Tool

Command-line interface for building, linting, and managing Copperhead projects.
"""

import argparse
import sys
import os
import subprocess
from pathlib import Path
from typing import List, Optional

from . import __version__
from .parser import parse_source, parse_file, find_rpbs
from .transpiler import transpile_source, transpile_module


def main():
    """Main entry point for the Copperhead CLI."""
    parser = argparse.ArgumentParser(
        prog="copperhead",
        description="Copperhead: A Granular Transpilation Framework for Seamless Rust-Python Interoperability"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Generate command (LLM-powered)
    gen_parser = subparsers.add_parser("generate", help="Generate Copperhead code from natural language")
    gen_parser.add_argument("description", nargs="?", help="Description of code to generate")
    gen_parser.add_argument("-o", "--output", default="generated_module", help="Output filename (without extension)")
    gen_parser.add_argument("-m", "--model", default="maryasov/qwen2.5-coder-cline:latest", help="Ollama model to use")
    gen_parser.add_argument("--no-test", action="store_true", help="Skip automatic test generation")
    gen_parser.add_argument("--max-iterations", type=int, default=3, help="Maximum refinement iterations")
    
    # Interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Start interactive code generation mode")
    interactive_parser.add_argument("-m", "--model", default="maryasov/qwen2.5-coder-cline:latest", help="Ollama model to use")
    
    # Build command
    build_parser = subparsers.add_parser("build", help="Build Copperhead modules")
    build_parser.add_argument("source", help="Source file or directory to build")
    build_parser.add_argument("-o", "--output", help="Output name for the compiled module")
    build_parser.add_argument("-m", "--mode", choices=["module", "bundle"], default="module",
                             help="Compilation mode: module (incremental) or bundle (monolithic)")
    build_parser.add_argument("--target", default="rust", help="Compilation target (default: rust)")
    build_parser.add_argument("--release", action="store_true", help="Build in release mode")
    build_parser.add_argument("--no-cache", action="store_true", help="Disable compilation cache")
    
    # Lint command
    lint_parser = subparsers.add_parser("lint", help="Lint Copperhead code for dynamic fallbacks")
    lint_parser.add_argument("source", help="Source file or directory to lint")
    lint_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed output")
    
    # Transpile command
    transpile_parser = subparsers.add_parser("transpile", help="Transpile Python to Rust code")
    transpile_parser.add_argument("source", help="Source file to transpile")
    transpile_parser.add_argument("-o", "--output", help="Output file for Rust code")
    transpile_parser.add_argument("--show-ast", action="store_true", help="Show AST before transpilation")
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check Copperhead code for errors")
    check_parser.add_argument("source", help="Source file or directory to check")
    
    # Cache command
    cache_parser = subparsers.add_parser("cache", help="Manage Copperhead cache")
    cache_parser.add_argument("action", choices=["clean", "show", "size"], help="Cache action")
    
    # Debug command
    debug_parser = subparsers.add_parser("debug", help="Debug Copperhead code")
    debug_parser.add_argument("source", help="Source file to debug")
    debug_parser.add_argument("--dry-run", action="store_true", help="Execute code in sandbox")
    debug_parser.add_argument("--validate", action="store_true", help="Validate code only")
    debug_parser.add_argument("--types", action="store_true", help="Check type annotations")
    
    # Registry command
    registry_parser = subparsers.add_parser("registry", help="Manage module registry")
    registry_parser.add_argument("action", choices=["list", "search", "add", "remove", "stats", "export"],
                                help="Registry action")
    registry_parser.add_argument("target", nargs="?", help="Target module or search query")
    registry_parser.add_argument("--tags", nargs="+", help="Filter by tags")
    registry_parser.add_argument("--output", help="Output directory for export")
    
    # Interpreter command
    interp_parser = subparsers.add_parser("interpret", help="Start interactive interpreter")
    interp_parser.add_argument("--no-agent", action="store_true", help="Disable AI agent")
    interp_parser.add_argument("-m", "--model", default="maryasov/qwen2.5-coder-cline:latest", help="Ollama model to use")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    try:
        if args.command == "generate":
            cmd_generate(args)
        elif args.command == "interactive":
            cmd_interactive(args)
        elif args.command == "build":
            cmd_build(args)
        elif args.command == "lint":
            cmd_lint(args)
        elif args.command == "transpile":
            cmd_transpile(args)
        elif args.command == "check":
            cmd_check(args)
        elif args.command == "cache":
            cmd_cache(args)
        elif args.command == "debug":
            cmd_debug(args)
        elif args.command == "registry":
            cmd_registry(args)
        elif args.command == "interpret":
            cmd_interpret(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_generate(args):
    """Handle generate command - LLM-powered code generation."""
    from .llm import CodeGenerator
    
    if not args.description:
        # If no description provided, enter interactive mode
        cmd_interactive(args)
        return
    
    print("Copperhead Code Generator")
    print("=" * 50)
    print(f"Description: {args.description}")
    print(f"Model: {args.model}")
    print()
    
    generator = CodeGenerator(model=args.model)
    result = generator.generate(
        description=args.description,
        output_name=args.output,
        auto_test=not args.no_test,
        max_iterations=args.max_iterations
    )
    
    if result.success and result.code:
        print("Code generated successfully!")
        print(f"Source saved to: generated/{args.output}.py")
        if result.code.tests_code:
            print(f"Tests saved to: generated/test_{args.output}.py")
        
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
        print("I need some clarifications:")
        for amb in result.code.ambiguities:
            print(f"\n{amb.question}")
            print(f"Context: {amb.context}")
            for i, opt in enumerate(amb.options, 1):
                print(f"  {i}. {opt}")
            print(f"Recommendation: {amb.recommendation}")
    
    else:
        print("Failed to generate code:")
        for error in result.errors:
            print(f"  - {error}")
        sys.exit(1)


def cmd_interactive(args):
    """Handle interactive command - interactive code generation."""
    from .llm import CodeGenerator
    
    generator = CodeGenerator(model=args.model)
    generator.interact()


def cmd_interpret(args):
    """Handle interpret command - start the interpreter."""
    from .interpreter import start_interpreter
    
    use_agent = not args.no_agent
    start_interpreter(use_agent=use_agent)


def cmd_debug(args):
    """Handle debug command - debug Copperhead code."""
    from .debugger import CopperheadDebugger, CodeValidator
    
    source_path = Path(args.source)
    
    if not source_path.exists():
        print(f"Error: Source path '{args.source}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
    
    debugger = CopperheadDebugger()
    validator = CodeValidator()
    
    print(f"Debugging {source_path}...")
    print("=" * 50)
    
    if args.validate or args.types:
        # Run specific checks
        if args.types:
            print("\nType Checking:")
            print("-" * 30)
            result = validator.validate_types(source)
            for msg in result.messages:
                severity_color = {
                    "INFO": "\033[94m",    # Blue
                    "WARNING": "\033[93m",  # Yellow
                    "ERROR": "\033[91m",    # Red
                    "CRITICAL": "\033[95m"  # Magenta
                }.get(msg.severity.name, "")
                reset_color = "\033[0m"
                
                print(f"{severity_color}[{msg.severity.name}]{reset_color} {msg.message}")
                if msg.line:
                    print(f"  Line {msg.line}")
                if msg.suggestion:
                    print(f"  Suggestion: {msg.suggestion}")
    else:
        # Full debug
        result = debugger.debug(source, str(source_path))
        
        # Print messages
        if result.messages:
            print("\nMessages:")
            print("-" * 30)
            for msg in result.messages:
                severity_color = {
                    "INFO": "\033[94m",    # Blue
                    "WARNING": "\033[93m",  # Yellow
                    "ERROR": "\033[91m",    # Red
                    "CRITICAL": "\033[95m"  # Magenta
                }.get(msg.severity.name, "")
                reset_color = "\033[0m"
                
                print(f"{severity_color}[{msg.severity.name}]{reset_color} {msg.message}")
                if msg.line:
                    print(f"  Line {msg.line}")
                if msg.suggestion:
                    print(f"  Suggestion: {msg.suggestion}")
        
        # Print type issues
        if result.type_issues:
            print("\nType Issues:")
            print("-" * 30)
            for issue in result.type_issues:
                print(f"Variable '{issue.variable}': expected {issue.expected}, got {issue.actual}")
                print(f"  Line {issue.line}: {issue.message}")
        
        # Print execution output
        if result.execution_output:
            print("\nExecution Output:")
            print("-" * 30)
            print(result.execution_output)
        
        if result.execution_error:
            print("\nExecution Error:")
            print("-" * 30)
            print(result.execution_error)
        
        # Print suggestions
        if result.suggestions:
            print("\nSuggestions:")
            print("-" * 30)
            for i, suggestion in enumerate(result.suggestions, 1):
                print(f"{i}. {suggestion}")
        
        # Summary
        print("\n" + "=" * 50)
        if result.success:
            print("\033[92m✓ Debug completed successfully\033[0m")
        else:
            print("\033[91m✗ Debug found issues\033[0m")
            sys.exit(1)


def cmd_registry(args):
    """Handle registry command - manage module registry."""
    from .registry import get_registry, ModuleMetadata, FunctionSignature, ModuleStatus
    
    registry = get_registry()
    
    if args.action == "list":
        print("Registered Modules:")
        print("=" * 50)
        
        modules = registry.get_all_modules()
        
        if not modules:
            print("No modules registered yet.")
            print("\nTo add a module, use: copperhead registry add <file.py>")
            return
        
        for module in modules:
            status_color = {
                ModuleStatus.DRAFT: "\033[93m",    # Yellow
                ModuleStatus.COMPILED: "\033[92m",  # Green
                ModuleStatus.FAILED: "\033[91m",    # Red
                ModuleStatus.DEPRECATED: "\033[90m" # Gray
            }.get(module.status, "")
            reset_color = "\033[0m"
            
            print(f"\n{status_color}{module.name}{reset_color} (v{module.version})")
            print(f"  ID: {module.id}")
            print(f"  Status: {status_color}{module.status.name}{reset_color}")
            print(f"  Description: {module.description}")
            print(f"  Functions: {len(module.functions)}")
            print(f"  Usage: {module.usage_count} times")
            if module.tags:
                print(f"  Tags: {', '.join(module.tags)}")
    
    elif args.action == "search":
        if not args.target:
            print("Error: Please provide a search query", file=sys.stderr)
            sys.exit(1)
        
        print(f"Searching for: {args.target}")
        print("=" * 50)
        
        modules = registry.search_modules(
            args.target,
            tags=args.tags,
            limit=10
        )
        
        if not modules:
            print("No modules found.")
            return
        
        for module in modules:
            print(f"\n{module.name} (v{module.version})")
            print(f"  Description: {module.description}")
            print(f"  Functions:")
            for func in module.functions[:5]:
                args_str = ", ".join([f"{n}: {t}" for n, t in func.args])
                print(f"    - {func.name}({args_str}) -> {func.return_type}")
    
    elif args.action == "add":
        if not args.target:
            print("Error: Please provide a file path", file=sys.stderr)
            sys.exit(1)
        
        source_path = Path(args.target)
        if not source_path.exists():
            print(f"Error: File '{args.target}' does not exist", file=sys.stderr)
            sys.exit(1)
        
        print(f"Adding {source_path} to registry...")
        
        module = registry.import_module(str(source_path))
        
        if module:
            print(f"✓ Added {module.name} (ID: {module.id})")
            print(f"  Functions: {len(module.functions)}")
        else:
            print("✗ Failed to add module")
            sys.exit(1)
    
    elif args.action == "remove":
        if not args.target:
            print("Error: Please provide a module ID", file=sys.stderr)
            sys.exit(1)
        
        print(f"Removing module {args.target}...")
        
        if registry.delete_module(args.target):
            print(f"✓ Removed module {args.target}")
        else:
            print(f"✗ Module {args.target} not found")
            sys.exit(1)
    
    elif args.action == "stats":
        stats = registry.get_stats()
        
        print("Registry Statistics:")
        print("=" * 50)
        print(f"Total Modules: {stats['total_modules']}")
        print(f"Total Functions: {stats['total_functions']}")
        print(f"Total Usage: {stats['total_usage']}")
        
        if stats['status_counts']:
            print("\nStatus Breakdown:")
            status_names = {0: "DRAFT", 1: "COMPILED", 2: "FAILED", 3: "DEPRECATED"}
            for status, count in stats['status_counts'].items():
                print(f"  {status_names.get(status, 'UNKNOWN')}: {count}")
    
    elif args.action == "export":
        if not args.target:
            print("Error: Please provide a module ID", file=sys.stderr)
            sys.exit(1)
        
        output_dir = args.output or f"export_{args.target}"
        
        print(f"Exporting module {args.target} to {output_dir}...")
        
        if registry.export_module(args.target, output_dir):
            print(f"✓ Exported to {output_dir}")
        else:
            print(f"✗ Failed to export module {args.target}")
            sys.exit(1)


def cmd_build(args):
    """Handle build command."""
    source_path = Path(args.source)
    
    if not source_path.exists():
        print(f"Error: Source path '{args.source}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if source_path.is_file():
        # Single file build
        build_single_file(source_path, args)
    elif source_path.is_dir():
        # Directory build
        build_directory(source_path, args)
    else:
        print(f"Error: '{args.source}' is not a file or directory", file=sys.stderr)
        sys.exit(1)


def build_single_file(source_path: Path, args):
    """Build a single Python file."""
    print(f"Building {source_path}...")
    
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Parse source
    module_info = parse_source(source, str(source_path))
    
    if module_info.rpb_count == 0:
        print(f"No Rich Python Blocks found in {source_path}")
        return
    
    print(f"Found {module_info.rpb_count} Rich Python Block(s)")
    
    # Transpile to Rust
    rust_code = transpile_module(module_info)
    
    # Determine output name
    output_name = args.output or source_path.stem
    
    # Create build directory
    build_dir = Path(f"build_{output_name}")
    build_dir.mkdir(exist_ok=True)
    
    # Write Rust code
    rust_file = build_dir / "lib.rs"
    with open(rust_file, 'w', encoding='utf-8') as f:
        f.write(rust_code)
    
    print(f"Generated Rust code: {rust_file}")
    
    # Generate Cargo.toml
    from .transpiler import generate_cargo_toml
    cargo_toml = generate_cargo_toml(output_name)
    cargo_file = build_dir / "Cargo.toml"
    with open(cargo_file, 'w', encoding='utf-8') as f:
        f.write(cargo_toml)
    
    print(f"Generated Cargo.toml: {cargo_file}")
    
    # Generate build script
    from .transpiler import generate_build_script
    build_script = generate_build_script()
    script_file = build_dir / "build.py"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(build_script)
    
    print(f"Generated build script: {script_file}")
    
    # Try to build with maturin if available
    if not args.no_cache:
        try:
            print("Attempting to build with maturin...")
            result = subprocess.run(
                [sys.executable, "-m", "maturin", "build", "--release"],
                cwd=build_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("Build successful!")
            else:
                print(f"Maturin build failed: {result.stderr}")
                print("You can manually build with: python build.py")
        except FileNotFoundError:
            print("Maturin not found. Install with: pip install maturin")
            print("Or manually build with: python build.py")


def build_directory(source_path: Path, args):
    """Build all Python files in a directory."""
    print(f"Building directory {source_path}...")
    
    python_files = list(source_path.glob("**/*.py"))
    
    if not python_files:
        print("No Python files found")
        return
    
    print(f"Found {len(python_files)} Python file(s)")
    
    # Collect all RPBs
    all_rpbs = []
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                source = f.read()
            
            rpbs = find_rpbs(source)
            for rpb in rpbs:
                all_rpbs.append((py_file, rpb))
        except Exception as e:
            print(f"Warning: Could not parse {py_file}: {e}")
    
    print(f"Found {len(all_rpbs)} total Rich Python Block(s)")
    
    if args.mode == "bundle":
        # Monolithic build - combine all RPBs
        print("Building in monolithic (bundle) mode...")
        # This would combine all RPBs into a single module
        # For now, just build each file separately
        for py_file in python_files:
            build_single_file(py_file, args)
    else:
        # Module build - individual files
        for py_file in python_files:
            build_single_file(py_file, args)


def cmd_lint(args):
    """Handle lint command."""
    source_path = Path(args.source)
    
    if not source_path.exists():
        print(f"Error: Source path '{args.source}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if source_path.is_file():
        lint_file(source_path, args.verbose)
    elif source_path.is_dir():
        for py_file in source_path.glob("**/*.py"):
            lint_file(py_file, args.verbose)


def lint_file(source_path: Path, verbose: bool = False):
    """Lint a single Python file."""
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(f"Error reading {source_path}: {e}")
        return
    
    # Parse source
    module_info = parse_source(source, str(source_path))
    
    issues = []
    
    # Check for dynamic fallbacks in RPBs
    for func in module_info.functions:
        if func.is_rpb:
            # Check for untyped arguments
            for arg in func.args:
                if arg.type_info is None:
                    issues.append(f"  {func.name}(): Argument '{arg.name}' lacks type annotation")
            
            # Check for dynamic types
            if func.return_type is None:
                issues.append(f"  {func.name}(): Missing return type annotation")
    
    if issues:
        print(f"Warning: {source_path}")
        for issue in issues:
            print(issue)
        if verbose:
            print(f"  Total issues: {len(issues)}")
    elif verbose:
        print(f"OK: {source_path}")


def cmd_transpile(args):
    """Handle transpile command."""
    source_path = Path(args.source)
    
    if not source_path.exists():
        print(f"Error: Source path '{args.source}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
    
    if args.show_ast:
        # Show AST
        import ast
        tree = ast.parse(source)
        print("AST:")
        print(ast.dump(tree, indent=2))
        print()
    
    # Transpile
    rust_code = transpile_source(source, str(source_path))
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(rust_code)
        print(f"Rust code written to: {args.output}")
    else:
        print(rust_code)


def cmd_check(args):
    """Handle check command."""
    source_path = Path(args.source)
    
    if not source_path.exists():
        print(f"Error: Source path '{args.source}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if source_path.is_file():
        check_file(source_path)
    elif source_path.is_dir():
        for py_file in source_path.glob("**/*.py"):
            check_file(py_file)


def check_file(source_path: Path):
    """Check a single Python file for syntax errors."""
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(f"Error reading {source_path}: {e}")
        return
    
    try:
        import ast
        ast.parse(source)
        print(f"OK: {source_path}")
    except SyntaxError as e:
        print(f"Syntax error in {source_path}: {e}")


def cmd_cache(args):
    """Handle cache command."""
    cache_dir = Path("__copperhead_cache__")
    
    if args.action == "clean":
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
            print("Cache cleaned")
        else:
            print("No cache found")
    
    elif args.action == "show":
        if cache_dir.exists():
            files = list(cache_dir.glob("*"))
            print(f"Cache contains {len(files)} file(s):")
            for f in files:
                print(f"  {f.name}")
        else:
            print("No cache found")
    
    elif args.action == "size":
        if cache_dir.exists():
            total_size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
            print(f"Cache size: {total_size / 1024:.2f} KB")
        else:
            print("No cache found")


if __name__ == "__main__":
    main()
