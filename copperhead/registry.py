"""
Copperhead Module Registry

A database system for storing, searching, and reusing compiled Copperhead modules.
Stores metadata, descriptions, function signatures, and dependencies.
"""

import json
import os
import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum, auto


class ModuleStatus(Enum):
    """Status of a module in the registry."""
    DRAFT = auto()       # Not yet compiled
    COMPILED = auto()    # Successfully compiled
    FAILED = auto()      # Compilation failed
    DEPRECATED = auto()  # No longer recommended


@dataclass
class FunctionSignature:
    """Signature of a function in a module."""
    name: str
    args: List[Tuple[str, str]]  # (name, type)
    return_type: str
    description: str = ""
    is_rpb: bool = False
    no_gil: bool = False
    examples: List[str] = field(default_factory=list)


@dataclass
class ModuleMetadata:
    """Metadata for a registered module."""
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    functions: List[FunctionSignature] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    status: ModuleStatus = ModuleStatus.DRAFT
    source_path: Optional[str] = None
    compiled_path: Optional[str] = None
    rust_code: Optional[str] = None
    tests_code: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    usage_count: int = 0
    rating: float = 0.0


class ModuleRegistry:
    """Registry for storing and managing Copperhead modules."""
    
    def __init__(self, db_path: str = ".copperhead/registry.db"):
        self.db_path = db_path
        self.cache_dir = Path(".copperhead/cache")
        self.modules_dir = Path(".copperhead/modules")
        
        # Create directories
        dirname = os.path.dirname(db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.modules_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Modules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS modules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    version TEXT DEFAULT '1.0.0',
                    author TEXT,
                    tags TEXT,
                    status INTEGER DEFAULT 0,
                    source_path TEXT,
                    compiled_path TEXT,
                    rust_code TEXT,
                    tests_code TEXT,
                    created_at REAL,
                    updated_at REAL,
                    usage_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0
                )
            """)
            
            # Functions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS functions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_id TEXT,
                    name TEXT NOT NULL,
                    args TEXT,
                    return_type TEXT,
                    description TEXT,
                    is_rpb BOOLEAN,
                    no_gil BOOLEAN,
                    examples TEXT,
                    FOREIGN KEY (module_id) REFERENCES modules(id)
                )
            """)
            
            # Dependencies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dependencies (
                    module_id TEXT,
                    dependency TEXT,
                    FOREIGN KEY (module_id) REFERENCES modules(id)
                )
            """)
            
            # Search index for descriptions
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS module_search 
                USING fts5(name, description, tags)
            """)
            
            conn.commit()
    
    def register_module(self, metadata: ModuleMetadata) -> str:
        """Register a new module in the registry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert module
            cursor.execute("""
                INSERT OR REPLACE INTO modules 
                (id, name, description, version, author, tags, status,
                 source_path, compiled_path, rust_code, tests_code,
                 created_at, updated_at, usage_count, rating)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.id,
                metadata.name,
                metadata.description,
                metadata.version,
                metadata.author,
                json.dumps(metadata.tags),
                metadata.status.value,
                metadata.source_path,
                metadata.compiled_path,
                metadata.rust_code,
                metadata.tests_code,
                metadata.created_at,
                metadata.updated_at,
                metadata.usage_count,
                metadata.rating
            ))
            
            # Insert functions
            for func in metadata.functions:
                cursor.execute("""
                    INSERT INTO functions 
                    (module_id, name, args, return_type, description, 
                     is_rpb, no_gil, examples)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metadata.id,
                    func.name,
                    json.dumps(func.args),
                    func.return_type,
                    func.description,
                    func.is_rpb,
                    func.no_gil,
                    json.dumps(func.examples)
                ))
            
            # Insert dependencies
            for dep in metadata.dependencies:
                cursor.execute("""
                    INSERT INTO dependencies (module_id, dependency)
                    VALUES (?, ?)
                """, (metadata.id, dep))
            
            # Update search index
            cursor.execute("""
                INSERT INTO module_search (name, description, tags)
                VALUES (?, ?, ?)
            """, (
                metadata.name,
                metadata.description,
                " ".join(metadata.tags)
            ))
            
            conn.commit()
        
        return metadata.id
    
    def get_module(self, module_id: str) -> Optional[ModuleMetadata]:
        """Get a module by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM modules WHERE id = ?
            """, (module_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Get functions
            cursor.execute("""
                SELECT * FROM functions WHERE module_id = ?
            """, (module_id,))
            
            func_rows = cursor.fetchall()
            functions = []
            for func_row in func_rows:
                functions.append(FunctionSignature(
                    name=func_row[2],
                    args=json.loads(func_row[3]),
                    return_type=func_row[4],
                    description=func_row[5],
                    is_rpb=bool(func_row[6]),
                    no_gil=bool(func_row[7]),
                    examples=json.loads(func_row[8])
                ))
            
            # Get dependencies
            cursor.execute("""
                SELECT dependency FROM dependencies WHERE module_id = ?
            """, (module_id,))
            
            deps = [row[0] for row in cursor.fetchall()]
            
            return ModuleMetadata(
                id=row[0],
                name=row[1],
                description=row[2],
                version=row[3],
                author=row[4],
                tags=json.loads(row[5]),
                functions=functions,
                dependencies=deps,
                status=ModuleStatus(row[6]),
                source_path=row[7],
                compiled_path=row[8],
                rust_code=row[9],
                tests_code=row[10],
                created_at=row[11],
                updated_at=row[12],
                usage_count=row[13],
                rating=row[14]
            )
    
    def search_modules(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        status: Optional[ModuleStatus] = None,
        limit: int = 10
    ) -> List[ModuleMetadata]:
        """Search for modules by query and filters."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Build search query
            if query:
                # Use LIKE for simple text search
                cursor.execute("""
                    SELECT * FROM modules 
                    WHERE name LIKE ? OR description LIKE ?
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", limit))
            else:
                # No query, get all
                sql = "SELECT * FROM modules WHERE 1=1"
                params = []
                
                if status:
                    sql += " AND status = ?"
                    params.append(status.value)
                
                sql += f" LIMIT {limit}"
                
                cursor.execute(sql, params)
            
            rows = cursor.fetchall()
            
            modules = []
            for row in rows:
                # Get functions
                cursor.execute("""
                    SELECT * FROM functions WHERE module_id = ?
                """, (row[0],))
                
                func_rows = cursor.fetchall()
                functions = []
                for func_row in func_rows:
                    functions.append(FunctionSignature(
                        name=func_row[2],
                        args=json.loads(func_row[3]),
                        return_type=func_row[4],
                        description=func_row[5],
                        is_rpb=bool(func_row[6]),
                        no_gil=bool(func_row[7]),
                        examples=json.loads(func_row[8])
                    ))
                
                # Get dependencies
                cursor.execute("""
                    SELECT dependency FROM dependencies WHERE module_id = ?
                """, (row[0],))
                deps = [r[0] for r in cursor.fetchall()]
                
                # Filter by tags if specified
                module_tags = json.loads(row[5])
                if tags and not any(t in module_tags for t in tags):
                    continue
                
                modules.append(ModuleMetadata(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    version=row[3],
                    author=row[4],
                    tags=module_tags,
                    functions=functions,
                    dependencies=deps,
                    status=ModuleStatus(row[6]),
                    source_path=row[7],
                    compiled_path=row[8],
                    rust_code=row[9],
                    tests_code=row[10],
                    created_at=row[11],
                    updated_at=row[12],
                    usage_count=row[13],
                    rating=row[14]
                ))
            
            return modules
    
    def search_functions(
        self,
        query: str,
        return_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Tuple[ModuleMetadata, FunctionSignature]]:
        """Search for functions across all modules."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Search functions by name or description
            sql = """
                SELECT f.*, m.name as module_name, m.description as module_desc
                FROM functions f
                JOIN modules m ON f.module_id = m.id
                WHERE (f.name LIKE ? OR f.description LIKE ?)
            """
            params = [f"%{query}%", f"%{query}%"]
            
            if return_type:
                sql += " AND f.return_type = ?"
                params.append(return_type)
            
            sql += f" LIMIT {limit}"
            
            cursor.execute(sql, params)
            
            results = []
            for row in cursor.fetchall():
                func = FunctionSignature(
                    name=row[2],
                    args=json.loads(row[3]),
                    return_type=row[4],
                    description=row[5],
                    is_rpb=bool(row[6]),
                    no_gil=bool(row[7]),
                    examples=json.loads(row[8])
                )
                
                # Get full module
                module = self.get_module(row[1])
                if module:
                    results.append((module, func))
            
            return results
    
    def get_all_modules(self) -> List[ModuleMetadata]:
        """Get all registered modules."""
        return self.search_modules(query=None, limit=1000)
    
    def delete_module(self, module_id: str) -> bool:
        """Delete a module from the registry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete from tables
            cursor.execute("DELETE FROM functions WHERE module_id = ?", (module_id,))
            cursor.execute("DELETE FROM dependencies WHERE module_id = ?", (module_id,))
            cursor.execute("DELETE FROM modules WHERE id = ?", (module_id,))
            
            conn.commit()
            
            return cursor.rowcount > 0
    
    def update_usage(self, module_id: str):
        """Increment usage count for a module."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE modules 
                SET usage_count = usage_count + 1, updated_at = ?
                WHERE id = ?
            """, (time.time(), module_id))
            conn.commit()
    
    def update_rating(self, module_id: str, rating: float):
        """Update rating for a module."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE modules 
                SET rating = ?, updated_at = ?
                WHERE id = ?
            """, (rating, time.time(), module_id))
            conn.commit()
    
    def export_module(self, module_id: str, output_dir: str) -> bool:
        """Export a module to files."""
        module = self.get_module(module_id)
        if not module:
            return False
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save source code
        if module.rust_code:
            with open(output_path / f"{module.name}.rs", 'w') as f:
                f.write(module.rust_code)
        
        # Save Python wrapper
        if module.source_path and os.path.exists(module.source_path):
            with open(output_path / f"{module.name}.py", 'w') as f:
                with open(module.source_path, 'r') as src:
                    f.write(src.read())
        
        # Save tests
        if module.tests_code:
            with open(output_path / f"test_{module.name}.py", 'w') as f:
                f.write(module.tests_code)
        
        # Save metadata
        with open(output_path / f"{module.name}.json", 'w') as f:
            json.dump(asdict(module), f, indent=2, default=str)
        
        return True
    
    def import_module(self, source_path: str) -> Optional[ModuleMetadata]:
        """Import a module from a Python file."""
        path = Path(source_path)
        if not path.exists():
            return None
        
        with open(path, 'r') as f:
            source_code = f.read()
        
        # Parse source to extract metadata
        from .parser import parse_source
        
        module_info = parse_source(source_code, str(path))
        
        # Extract functions
        functions = []
        for func in module_info.functions:
            functions.append(FunctionSignature(
                name=func.name,
                args=[(a.name, a.type_info.rust_type if a.type_info else "PyObject") 
                      for a in func.args],
                return_type=func.return_type.rust_type if func.return_type else "PyObject",
                description="",
                is_rpb=func.is_rpb,
                no_gil=func.no_gil
            ))
        
        # Generate module ID
        module_id = hashlib.md5(source_code.encode()).hexdigest()[:12]
        
        # Create metadata
        metadata = ModuleMetadata(
            id=module_id,
            name=path.stem,
            description=f"Imported from {path.name}",
            functions=functions,
            source_path=str(path.absolute()),
            status=ModuleStatus.COMPILED if module_info.rpb_count > 0 else ModuleStatus.DRAFT
        )
        
        # Register
        self.register_module(metadata)
        
        return metadata
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM modules")
            total_modules = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM functions")
            total_functions = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(usage_count) FROM modules")
            total_usage = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM modules 
                GROUP BY status
            """)
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                "total_modules": total_modules,
                "total_functions": total_functions,
                "total_usage": total_usage,
                "status_counts": status_counts
            }


# Global registry instance
_registry: Optional[ModuleRegistry] = None


def get_registry() -> ModuleRegistry:
    """Get the global registry instance."""
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry
