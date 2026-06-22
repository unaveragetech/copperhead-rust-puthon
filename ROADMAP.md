# Copperhead Roadmap

What we're building next.

---

## Current Status (v0.1.0)

**Working:**
- Full type system (16 primitive types)
- AST parser with type extraction
- Rust transpiler with PyO3 bindings
- Compiler pipeline (module and bundle modes)
- CLI with 10 commands
- AI agent with Ollama integration
- Module registry with SQLite
- Debugger with syntax/type/pattern checks
- Interactive interpreter
- 179 passing tests
- 52 comprehensive integration tests

---

## Phase 1: Foundation (In Progress)

### v0.1.1 - Bug Fixes
- [ ] Fix Windows path handling
- [ ] Improve error messages
- [ ] Add more test coverage

### v0.1.2 - Documentation
- [x] Complete API reference
- [x] Getting started guide
- [x] Tutorial with examples
- [x] Architecture deep dive
- [ ] Video tutorials

---

## Phase 2: Core Features

### v0.2.0 - Enhanced Transpilation
- [ ] Support for Python classes
- [ ] Lambda function transpilation
- [ ] List comprehension support
- [ ] Generator/iterator support
- [ ] Decorator chains

### v0.2.1 - Advanced Types
- [ ] Generic types (TypeVar)
- [ ] Protocol support
- [ ] Dataclass transpilation
- [ ] Enum support
- [ ] TypedDict support

---

## Phase 3: AI Agent

### v0.3.0 - Smarter AI
- [ ] Context-aware code generation
- [ ] Multi-file project support
- [ ] Refactoring suggestions
- [ ] Code review capabilities
- [ ] Test generation

### v0.3.1 - Agent Collaboration
- [ ] Multi-agent workflows
- [ ] Shared context between agents
- [ ] Agent specialization (types, patterns, etc.)
- [ ] Learning from user patterns

---

## Phase 4: Performance

### v0.4.0 - Optimization
- [ ] Cross-module inlining
- [ ] Dead code elimination
- [ ] Loop unrolling
- [ ] SIMD vectorization
- [ ] Profile-guided optimization

### v0.4.1 - Caching
- [ ] Content-addressable caching
- [ ] Distributed compilation
- [ ] Remote build cache
- [ ] Build time prediction

---

## Phase 5: Integration

### v0.5.0 - Library Support
- [ ] NumPy integration
- [ ] Pandas integration
- [ ] Async/await support
- [ ] Context managers
- [ ] Type stubs for popular libraries

### v0.5.1 - IDE Integration
- [ ] VS Code extension
- [ ] PyCharm plugin
- [ ] Real-time type checking
- [ ] Inline performance hints
- [ ] One-click compilation

---

## Phase 6: Production

### v0.6.0 - Enterprise Features
- [ ] License management
- [ ] Usage analytics (opt-in)
- [ ] Cloud compilation
- [ ] Team collaboration
- [ ] CI/CD integration

### v0.6.1 - Distribution
- [ ] PyPI packages
- [ ] Docker images
- [ ] Homebrew formula
- [ ] Winget package
- [ ] Snap package

---

## Phase 7: Advanced

### v0.7.0 - Multi-Language
- [ ] C backend (via cffi)
- [ ] WebAssembly output
- [ ] LLVM IR generation
- [ ] Custom backends

### v0.7.1 - Domain Specific
- [ ] Data science DSL
- [ ] Game development DSL
- [ ] Web backend DSL
- [ ] Embedded systems DSL

---

## Long-Term Vision

### Year 1
- Stable v1.0 release
- 1000+ community modules
- Major IDE support
- Production deployments

### Year 2
- Multi-language support
- Cloud-native compilation
- Enterprise adoption
- Performance parity with hand-written Rust

### Year 3
- Standard library extensions
- Hardware acceleration
- Global developer community
- Industry standard for Python performance

---

## How to Contribute

1. **Pick an item** from the roadmap
2. **Open an issue** to discuss your approach
3. **Submit a PR** with tests
4. **Get it reviewed** and merged

### Priority Labels

- **P0**: Critical - blocks other work
- **P1**: High - important for next release
- **P2**: Medium - valuable but not urgent
- **P3**: Low - nice to have

---

## Questions?

Open an issue at [github.com/unaveragetech/Copperhead/issues](https://github.com/unaveragetech/Copperhead/issues)

---

**Last updated:** June 21, 2026
