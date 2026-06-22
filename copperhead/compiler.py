"""
Copperhead Compilation Pipeline

This module provides the full compilation pipeline for transforming
Python source code into optimized Rust binaries.
"""

import os
import sys
import subprocess
import shutil
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum, auto

from .parser import parse_source, parse_file, ModuleInfo
from .transpiler import (
    transpile_module, generate_cargo_toml,
    generate_pyproject_toml, generate_build_script
)


class CompilationMode(Enum):
    """Compilation modes."""
    MODULE = auto()      # Incremental module compilation
    BUNDLE = auto()      # Monolithic bundle compilation


class CompilationStatus(Enum):
    """Status of compilation."""
    PENDING = auto()
    COMPILING = auto()
    SUCCESS = auto()
    FAILED = auto()
    CACHED = auto()


@dataclass
class CompilationResult:
    """Result of a compilation."""
    status: CompilationStatus
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    compilation_time: float = 0.0
    from_cache: bool = False


@dataclass
class BuildConfig:
    """Build configuration."""
    source_path: str
    output_name: Optional[str] = None
    mode: CompilationMode = CompilationMode.MODULE
    target: str = "rust"
    release: bool = True
    use_cache: bool = True
    cache_dir: str = "__copperhead_cache__"
    build_dir: str = "build"


class CopperheadCompiler:
    """Main compiler class for Copperhead."""
    
    def __init__(self, config: BuildConfig):
        self.config = config
        self.cache_dir = Path(config.cache_dir)
        self.build_dir = Path(config.build_dir)
        
        # Ensure directories exist
        self.cache_dir.mkdir(exist_ok=True)
        self.build_dir.mkdir(exist_ok=True)
    
    def compile(self) -> CompilationResult:
        """Compile the source code."""
        import time
        start_time = time.time()
        
        source_path = Path(self.config.source_path)
        
        if not source_path.exists():
            return CompilationResult(
                status=CompilationStatus.FAILED,
                error_message=f"Source path '{self.config.source_path}' does not exist"
            )
        
        try:
            if source_path.is_file():
                result = self._compile_file(source_path)
            elif source_path.is_dir():
                result = self._compile_directory(source_path)
            else:
                result = CompilationResult(
                    status=CompilationStatus.FAILED,
                    error_message=f"'{self.config.source_path}' is not a file or directory"
                )
        except Exception as e:
            result = CompilationResult(
                status=CompilationStatus.FAILED,
                error_message=str(e)
            )
        
        result.compilation_time = time.time() - start_time
        return result
    
    def _compile_file(self, source_path: Path) -> CompilationResult:
        """Compile a single file."""
        # Check cache first
        if self.config.use_cache:
            cached = self._check_cache(source_path)
            if cached:
                return CompilationResult(
                    status=CompilationStatus.CACHED,
                    output_path=str(cached),
                    from_cache=True
                )
        
        # Parse source
        module_info = parse_file(str(source_path))
        
        if module_info.rpb_count == 0:
            return CompilationResult(
                status=CompilationStatus.SUCCESS,
                output_path=None
            )
        
        # Transpile to Rust
        rust_code = transpile_module(module_info)
        
        # Determine output name
        output_name = self.config.output_name or source_path.stem
        
        # Create build directory
        build_path = self.build_dir / output_name
        build_path.mkdir(exist_ok=True)
        
        # Write Rust code
        rust_file = build_path / "lib.rs"
        with open(rust_file, 'w', encoding='utf-8') as f:
            f.write(rust_code)
        
        # Generate Cargo.toml
        cargo_toml = generate_cargo_toml(output_name)
        cargo_file = build_path / "Cargo.toml"
        with open(cargo_file, 'w', encoding='utf-8') as f:
            f.write(cargo_toml)
        
        # Generate pyproject.toml
        pyproject_toml = generate_pyproject_toml(output_name)
        pyproject_file = build_path / "pyproject.toml"
        with open(pyproject_file, 'w', encoding='utf-8') as f:
            f.write(pyproject_toml)
        
        # Generate build script
        build_script = generate_build_script()
        script_file = build_path / "build.py"
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(build_script)
        
        # Try to compile with cargo
        compile_result = self._run_cargo_build(build_path)
        
        if compile_result.status == CompilationStatus.SUCCESS:
            # Cache the result
            if self.config.use_cache:
                self._update_cache(source_path, compile_result.output_path)
        
        return compile_result
    
    def _compile_directory(self, source_path: Path) -> CompilationResult:
        """Compile all files in a directory."""
        python_files = list(source_path.glob("**/*.py"))
        
        if not python_files:
            return CompilationResult(
                status=CompilationStatus.SUCCESS,
                output_path=None
            )
        
        if self.config.mode == CompilationMode.BUNDLE:
            return self._compile_bundle(python_files)
        else:
            return self._compile_modules(python_files)
    
    def _compile_bundle(self, python_files: List[Path]) -> CompilationResult:
        """Compile all files as a single bundle."""
        # Parse all files and combine
        all_modules = []
        for py_file in python_files:
            try:
                module_info = parse_file(str(py_file))
                all_modules.append(module_info)
            except Exception as e:
                print(f"Warning: Could not parse {py_file}: {e}")
        
        # Combine all RPBs
        combined_functions = []
        combined_imports = []
        rpb_count = 0
        
        for module in all_modules:
            combined_functions.extend(module.functions)
            combined_imports.extend(module.imports)
            rpb_count += module.rpb_count
        
        if rpb_count == 0:
            return CompilationResult(
                status=CompilationStatus.SUCCESS,
                output_path=None
            )
        
        # Create combined module info
        combined_module = ModuleInfo(
            path=str(source_path),
            functions=combined_functions,
            imports=list(set(combined_imports)),
            rpb_count=rpb_count
        )
        
        # Transpile
        rust_code = transpile_module(combined_module)
        
        # Determine output name
        output_name = self.config.output_name or "copperhead_bundle"
        
        # Create build directory
        build_path = self.build_dir / output_name
        build_path.mkdir(exist_ok=True)
        
        # Write files
        rust_file = build_path / "lib.rs"
        with open(rust_file, 'w', encoding='utf-8') as f:
            f.write(rust_code)
        
        cargo_toml = generate_cargo_toml(output_name)
        cargo_file = build_path / "Cargo.toml"
        with open(cargo_file, 'w', encoding='utf-8') as f:
            f.write(cargo_toml)
        
        # Compile
        return self._run_cargo_build(build_path)
    
    def _compile_modules(self, python_files: List[Path]) -> CompilationResult:
        """Compile each file as a separate module."""
        results = []
        
        for py_file in python_files:
            original_output = self.config.output_name
            self.config.output_name = None  # Let it auto-detect
            
            result = self._compile_file(py_file)
            results.append(result)
            
            self.config.output_name = original_output
        
        # Check if any failed
        failed = [r for r in results if r.status == CompilationStatus.FAILED]
        if failed:
            return CompilationResult(
                status=CompilationStatus.FAILED,
                error_message=f"Failed to compile {len(failed)} file(s)"
            )
        
        return CompilationResult(
            status=CompilationStatus.SUCCESS,
            output_path=str(self.build_dir)
        )
    
    def _run_cargo_build(self, build_path: Path) -> CompilationResult:
        """Run cargo build."""
        try:
            # Check if cargo is available
            subprocess.run(
                ["cargo", "--version"],
                capture_output=True,
                check=True
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return CompilationResult(
                status=CompilationStatus.FAILED,
                error_message="Cargo not found. Please install Rust and Cargo."
            )
        
        # Run cargo build
        mode = "--release" if self.config.release else []
        
        try:
            result = subprocess.run(
                ["cargo", "build"] + mode,
                cwd=build_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                # Find the output library
                if sys.platform == "win32":
                    lib_name = f"{build_path.name}.dll"
                elif sys.platform == "darwin":
                    lib_name = f"lib{build_path.name}.dylib"
                else:
                    lib_name = f"lib{build_path.name}.so"
                
                output_path = build_path / "target" / ("release" if self.config.release else "debug") / lib_name
                
                if output_path.exists():
                    return CompilationResult(
                        status=CompilationStatus.SUCCESS,
                        output_path=str(output_path)
                    )
                else:
                    return CompilationResult(
                        status=CompilationStatus.SUCCESS,
                        output_path=str(build_path / "target")
                    )
            else:
                return CompilationResult(
                    status=CompilationStatus.FAILED,
                    error_message=f"Cargo build failed:\n{result.stderr}"
                )
        
        except subprocess.TimeoutExpired:
            return CompilationResult(
                status=CompilationStatus.FAILED,
                error_message="Compilation timed out (5 minute limit)"
            )
    
    def _check_cache(self, source_path: Path) -> Optional[Path]:
        """Check if a cached version exists."""
        cache_key = self._get_cache_key(source_path)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                output_path = Path(cache_data.get("output_path", ""))
                if output_path.exists():
                    return output_path
            except Exception:
                pass
        
        return None
    
    def _update_cache(self, source_path: Path, output_path: str):
        """Update the cache."""
        cache_key = self._get_cache_key(source_path)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        cache_data = {
            "source_path": str(source_path),
            "output_path": output_path,
            "timestamp": os.path.getmtime(source_path)
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
    
    def _get_cache_key(self, source_path: Path) -> str:
        """Generate cache key for a source file."""
        # Use file path and modification time as cache key
        mtime = os.path.getmtime(source_path)
        key = f"{source_path}_{mtime}"
        return hashlib.md5(key.encode()).hexdigest()


def compile_source(source: str, filename: str = "<unknown>", **kwargs) -> CompilationResult:
    """Compile Python source code."""
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(source)
        temp_path = f.name
    
    try:
        config = BuildConfig(source_path=temp_path, **kwargs)
        compiler = CopperheadCompiler(config)
        return compiler.compile()
    finally:
        os.unlink(temp_path)


def compile_file(filepath: str, **kwargs) -> CompilationResult:
    """Compile a Python file."""
    config = BuildConfig(source_path=filepath, **kwargs)
    compiler = CopperheadCompiler(config)
    return compiler.compile()


def compile_directory(dirpath: str, **kwargs) -> CompilationResult:
    """Compile all Python files in a directory."""
    config = BuildConfig(source_path=dirpath, **kwargs)
    compiler = CopperheadCompiler(config)
    return compiler.compile()
