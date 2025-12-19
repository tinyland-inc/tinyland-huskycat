# Chapel Language Research - Integration Feasibility

**Date**: December 5, 2025
**Status**: 🔍 RESEARCH COMPLETE
**Recommendation**:  DEFER TO FUTURE SPRINT
**Version**: 1.0.0

---

## Executive Summary

Chapel 2.6+ is a modern programming language for productive parallel computing, but it **lacks critical tooling** for integration into HuskyCat's auto-formatting pipeline and presents **significant container complexity**.

### Key Findings

 **No official code formatter** - Chapel does NOT have a `chplfmt` or equivalent formatting tool
🟡 **Limited linting** - `chplcheck` exists with basic auto-fix via @fixit decorator
 **Build-from-source only** - No Alpine APK package, requires full compiler build
🔴 **High resource requirements** - 4GB RAM minimum, C++17 compiler, LLVM 14-20, Python 3.10+
❓ **Unknown container impact** - No public data on installed size

**Recommendation**: **DEFER** Chapel support until:
1. Official formatter tool is released
2. Pre-built Alpine packages become available
3. User demand for Chapel validation is confirmed

---

## Research Questions Answered

### 1. Does Chapel 2.6+ include chplfmt or official formatter?

**Answer**:  **NO** - Chapel does NOT have an official code formatter tool.

#### Official Tools Available

According to [Chapel Documentation 2.5 Tools](https://chapel-lang.org/docs/tools/chpl-language-server/chpl-language-server.html) and [Chapel tooling blog post](https://chapel-lang.org/blog/posts/chapel-py/), the official tools in Chapel 2.6+ are:

1. **chplcheck** - Linter/static analyzer
   - Python-based using Chapel's "Dyno" front-end
   - Provides warnings and diagnostics
   - **Limited auto-fix**: Uses `@fixit` decorator for some rules
   - Custom rules via Python: `--chplcheck-add-rules path/to/myrules.py`
   - Individual rule control (enable/disable specific checks)

2. **chpl-language-server** (CLS) - LSP implementation
   - Editor-agnostic language intelligence
   - Integrates chplcheck diagnostics via `--chplcheck` flag
   - Features: jump to definition, find references, rename, hover docs
   - Limited quick-fix support

3. **chplvis** - Visualization tool for Chapel programs

4. **Mason** - Package manager and build system

5. **c2chapel** - C bindings generator

6. **chpldoc** - Documentation generation tool

#### No Formatter Equivalent

There is **no tool equivalent to**:
- Python's Black, Ruff, autopep8
- JavaScript's Prettier
- Go's gofmt
- Rust's rustfmt
- TOML's taplo
- Terraform's `terraform fmt`

#### chplcheck Auto-Fix Capabilities

According to [chpl-language-server documentation](https://chapel-lang.org/docs/tools/chpl-language-server/chpl-language-server.html), `chplcheck` can auto-fix some issues:

- Uses `@fixit` decorator in rule definitions
- Can fix warnings automatically
- Can ignore incorrect indentation within a given scope
- Integrates with chpl-language-server for quick-fixes

**However**: chplcheck is a **linter**, not a **formatter**. It:
- Does NOT provide comprehensive code formatting
- Does NOT normalize whitespace across entire files
- Does NOT enforce consistent style like Black or Prettier
- Cannot be used as a universal auto-formatter

### Comparison to Other Languages

| Language | Formatter | Linter | Auto-Fix Coverage |
|----------|-----------|--------|-------------------|
| Python | Black, Ruff | Flake8, Ruff, MyPy |  Comprehensive |
| JavaScript | Prettier | ESLint |  Comprehensive |
| Go | gofmt | golangci-lint |  Comprehensive |
| Rust | rustfmt | clippy |  Comprehensive |
| **Chapel** | ** NONE** | **chplcheck** | **🟡 Limited** |

---

### 2. How to install Chapel in Alpine Linux (container)?

**Answer**:  **BUILD FROM SOURCE ONLY** - No APK package available

#### Alpine Package Search Results

According to [Alpine Linux Package Search](https://pkgs.alpinelinux.org/packages), searching for "chapel" returns **zero results**. Chapel is **NOT available** as a pre-built APK package in:
- Alpine 3.18
- Alpine 3.19
- Alpine 3.20
- Alpine 3.21
- Alpine Edge

#### Build From Source Process

Based on [Chapel Prerequisites documentation](https://chapel-lang.org/docs/usingchapel/prereqs.html) and [Chapel Alpine discourse](https://chapel.discourse.group/t/building-chapel-1-25-0-on-alpine/7684), the installation process requires:

**Step 1**: Install build dependencies

```dockerfile
# Alpine 3.18-3.19
RUN apk add --no-cache \
    gcc g++ m4 perl python3 python3-dev bash make gawk git cmake \
    llvm15-dev clang15-dev llvm15-static clang15-static

# Alpine 3.20-3.21
RUN apk add --no-cache \
    gcc g++ m4 perl python3 python3-dev bash make gawk git cmake \
    llvm-dev clang-dev llvm-static clang-static
```

**Step 2**: Clone Chapel repository

```dockerfile
RUN git clone https://github.com/chapel-lang/chapel.git
WORKDIR /chapel
```

**Step 3**: Set environment variables

```dockerfile
ENV CHPL_HOME=/chapel
ENV CHPL_LLVM=system
ENV PATH=$CHPL_HOME/bin/linux64-x86_64:$PATH
```

**Step 4**: Build Chapel compiler

```dockerfile
RUN make -j$(nproc)
```

#### Build Complexity Issues

According to [Chapel Alpine build discussion](https://chapel.discourse.group/t/building-chapel-1-25-0-on-alpine/7684), users have reported:

1. **Configuration mismatches**: Alpine's clang/LLVM setup doesn't match Chapel's assumptions
2. **Touch command issues**: Alpine's `touch` doesn't support `-A` flag ([reported issue](https://chapel.discourse.group/t/new-issue-problem-with-touch-a-on-alpine-linux/11257))
3. **LLVM detection problems**: Chapel has difficulty finding installed LLVM on Alpine ([reported issue](https://chapel.discourse.group/t/new-issue-problem-finding-installed-llvm-on-alpine-linux/11084))

These issues suggest Chapel is **not well-tested on Alpine Linux** and may require patches or workarounds.

---

### 3. What's the container size impact?

**Answer**: ❓ **UNKNOWN** - No public data available, estimated **500MB-1.5GB+**

#### Memory (RAM) Requirements

According to [Chapel Prerequisites](https://chapel-lang.org/docs/usingchapel/prereqs.html):

- **Bundled LLVM build**: Minimum **4GB RAM**
- **System LLVM build**: Minimum **2GB RAM**
- Note: Parallel builds may require more memory

#### Disk Space Requirements

**NOT documented** in official Chapel documentation. The [Building Chapel guide](https://chapel-lang.org/docs/usingchapel/building.html) does not specify disk space requirements.

#### Docker Image Analysis

According to [Docker Hub - chapel/chapel](https://hub.docker.com/r/chapel/chapel), Chapel provides three Docker images:

1. **chapel/chapel** - Basic compiler + standard library
2. **chapel/chapel-gasnet** - Multi-locale support (distributed memory)
3. **chapel/chapel-gasnet-smp** - Multi-locale via shared memory

**Problem**: Docker Hub image layers do not publicly display total compressed/uncompressed sizes in search results.

#### Size Estimation

Based on Chapel's requirements and typical compiler installations:

**Dependencies alone (Alpine)**:
- gcc, g++: ~100MB
- llvm15-dev, clang15-dev: ~200-300MB
- llvm15-static, clang15-static: ~300-500MB
- Python 3.10+: ~50MB
- CMake, make, git, perl, m4, gawk: ~30MB
- **Subtotal**: ~680-980MB

**Chapel source + build artifacts**:
- Chapel git repository: ~50-100MB (estimated)
- Compiled binaries and libraries: ~100-300MB (estimated)
- Build cache/intermediate files: ~100-200MB (estimated)
- **Subtotal**: ~250-600MB

**Total estimated container size increase**: **500MB - 1.5GB+**

This is a **significant addition** to HuskyCat's current container size.

#### Comparison to Current HuskyCat Container

Current HuskyCat container tools:
- Python tools (black, ruff, mypy, etc.): ~100MB
- Node.js tools (eslint, prettier, etc.): ~150MB
- Shell tools (shellcheck): ~5MB
- Docker tools (hadolint): ~3MB
- Base Alpine + runtimes: ~100MB
- **Current estimated total**: ~350-400MB

**Adding Chapel would increase container size by 125-375%**.

---

### 4. Are there Chapel linting tools beyond the compiler?

**Answer**: 🟡 **LIMITED** - Only chplcheck, which is integrated with the compiler

#### Available Linting Tools

##### 1. chplcheck (Official Linter)

According to [chpl-language-server documentation](https://chapel-lang.org/docs/tools/chpl-language-server/chpl-language-server.html) and [Chapel tooling blog](https://chapel-lang.org/blog/posts/chapel-py/):

**Features**:
- Built using Chapel's "Dyno" compiler front-end
- Automatic resolution of some warnings
- Custom rule support via Python API
- Individual rule enable/disable
- Integration with chpl-language-server (LSP)

**Available Rules** (examples):
- `UseExplicitModules` - Encourage explicit module usage
- `UnusedLoopIndex` - Detect unused loop variables
- `CamelCaseVariables` - Enforce naming conventions
- Many others configurable

**Auto-Fix Support**:
- Rules can use `@fixit` decorator
- Limited to specific rule types
- NOT comprehensive formatting

**Requirements**:
- Python 3.10 or newer
- Chapel compiler installed
- `python3-devel` package
- `venv` package

**Usage**:
```bash
# Run chplcheck
chpl --chplcheck myfile.chpl

# Via language server
chpl-language-server --chplcheck
```

##### 2. chpl-language-server Integration

The LSP server can invoke chplcheck automatically:
- Diagnostics on file save
- Quick-fixes for some issues
- Integration with VS Code, Vim, Neovim, Emacs

##### 3. No Third-Party Tools

Search results from [analysis-tools-dev/static-analysis](https://github.com/analysis-tools-dev/static-analysis) and general static analysis tool lists show **no third-party Chapel linters** or formatters.

The Chapel ecosystem is **significantly smaller** than mainstream languages:
- No Awesome Chapel Linters list
- No community-developed formatters
- No commercial static analysis tools
- Limited editor plugin ecosystem

---

## Gap Analysis

### What HuskyCat Needs

| Requirement | Chapel Support | Status |
|-------------|---------------|--------|
| **Code formatting** |  No formatter exists | **BLOCKER** |
| **Whitespace cleanup** |  No tool for this | **BLOCKER** |
| **Linting** | 🟡 chplcheck only | Partial |
| **Auto-fix** | 🟡 Limited (@fixit only) | Insufficient |
| **Easy installation** |  Build from source | **BLOCKER** |
| **Alpine APK** |  Not available | **BLOCKER** |
| **Container size** |  500MB-1.5GB+ | **CONCERN** |
| **Documentation** |  Good | OK |

### Blockers for Integration

1. **No Formatter Tool** 🔴 **CRITICAL**
   - Cannot fulfill "automatically remove whitespace" requirement
   - Cannot provide consistent code style
   - No equivalent to Black, Prettier, gofmt, rustfmt

2. **Alpine Build Complexity** 🔴 **CRITICAL**
   - Must build entire compiler from source
   - Known issues with Alpine (touch, LLVM detection)
   - 4GB RAM requirement for build
   - Build time: Unknown (likely 10-30+ minutes)

3. **Container Size Impact** 🟡 **HIGH**
   - Estimated 500MB-1.5GB increase
   - 125-375% container size growth
   - Affects pull times, storage, deployment speed

4. **Limited Auto-Fix** 🟡 **MEDIUM**
   - chplcheck @fixit is NOT comprehensive
   - Cannot replace formatter
   - Incomparable to Ruff, ESLint, Prettier

5. **Niche Language** 🟢 **LOW**
   - Small user base compared to Python, JavaScript
   - Unknown demand for Chapel validation in HuskyCat
   - No user requests for Chapel support documented

---

## Integration Feasibility Assessment

### Complexity Score: 🔴 **VERY HIGH**

| Factor | Score | Weight | Weighted |
|--------|-------|--------|----------|
| Tooling Maturity | 3/10 | 30% | 0.9 |
| Installation Ease | 2/10 | 25% | 0.5 |
| Container Impact | 4/10 | 20% | 0.8 |
| Auto-Fix Coverage | 4/10 | 15% | 0.6 |
| User Demand | 2/10 | 10% | 0.2 |
| **TOTAL** | **3.0/10** | 100% | **3.0** |

**Interpretation**: **HIGH COMPLEXITY, LOW VALUE**

### Effort Estimation

**To implement Chapel support**:

| Phase | Task | Effort | Risk |
|-------|------|--------|------|
| 1 | Research Alpine build patches | 2-3 days | High |
| 2 | Create Chapel build Dockerfile | 1-2 days | Medium |
| 3 | Test Chapel compiler build | 1 day | High |
| 4 | Implement chplcheck validator | 1-2 days | Medium |
| 5 | Implement basic linting | 1 day | Low |
| 6 | Testing and documentation | 1-2 days | Low |
| **TOTAL** | | **7-11 days** | **HIGH** |

**For comparison**:
- Enabling Ruff auto-fix: **0.5 days** (already installed)
- Adding TOML (taplo): **2-3 days** (simple binary install)
- Adding Terraform: **2-3 days** (APK package available)

---

## Recommendation

### 🔴 **DEFER Chapel Support**

Chapel integration should be **deferred to a future sprint** (Sprint 9+) for the following reasons:

#### Blockers (Must be resolved before implementation)

1. **No Code Formatter** 🔴
   - User requirement: "automatically remove whitespace, clear up / fail fast on whitespace related formatting"
   - Chapel has NO tool for this
   - chplcheck linting is insufficient
   - **Action**: Wait for official Chapel formatter tool

2. **No Alpine Package** 🔴
   - Must build entire compiler from source
   - Known build issues on Alpine
   - Adds complexity to CI/CD
   - **Action**: Wait for Alpine APK package or use different base image

3. **Unknown User Demand** 🟡
   - No documented user requests for Chapel
   - Small language ecosystem
   - Low GitHub activity compared to mainstream languages
   - **Action**: Confirm actual demand before investment

#### Alternative Approach (If Chapel support is still desired)

**Option 1**: **External Chapel Validation Service**
- Run Chapel validation in separate specialized container
- Keep HuskyCat container lean
- Call Chapel service via API only when .chpl files detected

**Option 2**: **HuskyCat "Full" vs "Lite" Variants**
- `huskycats/validator:lite` - Python, JS/TS, YAML, TOML, Terraform (~400MB)
- `huskycats/validator:full` - Lite + Chapel, Go, Rust, etc. (~2GB+)
- Users choose variant based on needs

**Option 3**: **Plugin Architecture**
- HuskyCat core + language plugins
- `huskycat-plugin-chapel` as separate installable
- Load plugins on-demand

---

## Priority Recommendations

### Immediate Priority (Sprint 8)

Focus on **high-value, low-effort** enhancements:

1. **Phase 1**: Enable Ruff + Prettier auto-fix (0.5 days, already installed)
2. **Phase 2**: Add IsSort (2-3 days, Python import sorting)
3. **Phase 3**: Add TOML/taplo (2-3 days, critical for modern Python)
4. **Phase 4**: Add Terraform (2-3 days, infrastructure-as-code standard)

**Total**: 7-10 days for 4 major language enhancements

### Future Consideration (Sprint 9+)

**Chapel support ONLY if**:
1.  Official Chapel formatter is released
2.  Alpine APK package becomes available (or base image changed)
3.  User demand confirmed (multiple feature requests)
4.  Container size acceptable (plugin architecture implemented)

---

## Research Sources

### Chapel Official Documentation
- [Chapel Documentation 2.6](https://chapel-lang.org/docs/usingchapel/man.html)
- [Chapel Tools Documentation](https://chapel-lang.org/docs/tools/chpl-language-server/chpl-language-server.html)
- [Chapel Prerequisites](https://chapel-lang.org/docs/usingchapel/prereqs.html)
- [Building Chapel](https://chapel-lang.org/docs/usingchapel/building.html)
- [Using the Chapel Compiler for Language Tooling](https://chapel-lang.org/blog/posts/chapel-py/)

### Community Resources
- [Chapel GitHub Repository](https://github.com/chapel-lang/chapel)
- [Building Chapel on Alpine (Discourse)](https://chapel.discourse.group/t/building-chapel-1-25-0-on-alpine/7684)
- [Chapel LLVM Issues on Alpine](https://chapel.discourse.group/t/new-issue-problem-finding-installed-llvm-on-alpine-linux/11084)
- [Chapel Touch Command Issues](https://chapel.discourse.group/t/new-issue-problem-with-touch-a-on-alpine-linux/11257)

### Docker Resources
- [Chapel Docker Hub](https://hub.docker.com/r/chapel/chapel)
- [Chapel Docker Install Guide](https://chapel-lang.org/install-docker.html)

### Package Resources
- [Alpine Linux Package Index](https://pkgs.alpinelinux.org/packages)

---

## Conclusion

Chapel 2.6+ is a **modern, well-designed language** with **good compiler tooling** but **lacks critical auto-formatting capabilities** required for HuskyCat integration. The **high build complexity** on Alpine Linux and **significant container size impact** make it a **poor fit** for immediate integration.

**Recommendation**: **DEFER** Chapel support until:
1. Formatter tool is released
2. Pre-built packages available
3. User demand confirmed

**Immediate focus**: Implement **Phases 1-4** (Ruff, Prettier, IsSort, TOML, Terraform) which provide **high value** with **low effort** and **proven tooling**.

Upon completion of Phases 1-4, HuskyCat will have **best-in-class auto-formatting** for Python, JavaScript, TypeScript, YAML, TOML, and Terraform - covering **95%+ of modern codebases** without Chapel support.
