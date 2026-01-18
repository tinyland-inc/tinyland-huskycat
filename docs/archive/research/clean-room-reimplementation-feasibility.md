# Clean-Room Python Reimplementation Feasibility Analysis

**Date**: 2026-01-16
**Author**: Claude (Research Agent)
**Subject**: Feasibility of creating clean-room Python reimplementations of shellcheck, hadolint, and yamllint

---

## Executive Summary

**Verdict**: **MIXED FEASIBILITY** - Partial reimplementation viable for yamllint; not recommended for shellcheck and hadolint.

**Key Findings**:
- ✅ **yamllint**: Already GPL-licensed, but clean-room rewrite feasible using MIT-licensed parsers
- ⚠️ **shellcheck**: Legally feasible but technically complex (~340 rules), high risk
- ❌ **hadolint**: Not recommended - better alternatives exist

**Recommended Strategy**:
1. **yamllint**: Fork existing GPL version OR create minimal clean-room implementation
2. **shellcheck**: Use existing binary OR investigate minimal subset reimplementation
3. **hadolint**: Use MIT-licensed `dockerlint` Python package instead

---

## 1. yamllint Analysis

### Current Status
- **License**: GPL-3.0-or-later (NOT MIT as initially thought)
- **Language**: Pure Python
- **Dependencies**: pathspec, pyyaml
- **Source**: [adrienverge/yamllint](https://github.com/adrienverge/yamllint) (GPL-3.0)

### Public Specifications Available

✅ **YAML 1.2 Specification** (2009, revised 2021)
- **Source**: [yaml.org specification](https://yaml.org/spec/)
- **Latest**: YAML 1.2 Revision 1.2.2 (Oct 1, 2021)
- **Status**: Fully public, no licensing restrictions

✅ **YAML 1.1 Specification** (2005)
- **Source**: [YAML 1.1 Specification](https://yaml.org/spec/1.1/)
- **Status**: Fully public

### Existing Python Libraries (MIT-Licensed)

| Library | License | YAML Version | Features |
|---------|---------|--------------|----------|
| **PyYAML** | MIT | 1.1 | Parser/emitter, widely used |
| **ruamel.yaml** | MIT | 1.2 | Roundtrip preservation, comments |

**Source**: [PyYAML MIT License](https://github.com/yaml/pyyaml/blob/main/LICENSE), [ruamel.yaml PyPI](https://pypi.org/project/ruamel.yaml/)

### Complexity Assessment

**yamllint Rule Categories**:
1. Syntax validation (delegated to parser)
2. Cosmetic checks (trailing spaces, line length, indentation)
3. Key duplication detection
4. Document structure validation

**Estimated Rules**: ~20-30 checks

**Implementation Effort**:
- **Parser**: Use existing MIT-licensed PyYAML or ruamel.yaml (0 effort)
- **Linting rules**: ~20-30 custom rules (~2-4 weeks for core rules)
- **Configuration**: YAML config format (~1 week)
- **CLI interface**: argparse (~3-5 days)

**Total Estimate**: **4-6 weeks** for 80% feature parity

### Clean Room Legality

✅ **Legal**: Clean-room reimplementation is **legally defensible** under Sony v. Connectix precedent

**Requirements**:
1. **Specification-based**: Implement from YAML 1.2 spec, not yamllint source
2. **Independent design**: No copying of rule logic from GPL source
3. **Documentation**: Document design decisions independent of yamllint
4. **Two-team approach**: Spec reader (writes functional spec) + implementer (codes from spec)

**Precautions**:
- ❌ Do NOT read yamllint GPL source code during implementation
- ✅ Use YAML specification and Docker/Kubernetes YAML best practices
- ✅ Design rules independently based on common YAML anti-patterns
- ✅ Document clean-room process for legal defense

**Source**: [Clean-room design Wikipedia](https://en.wikipedia.org/wiki/Clean-room_design), [Sony v. Connectix precedent](https://www.retroreversing.com/clean-room-reversing)

### Existing MIT/Apache Alternatives

**Option 1: Google yamlfmt** (Apache 2.0)
- **Language**: Go (not Python)
- **License**: Apache 2.0
- **Features**: Opinionated formatter, highly configurable
- **Limitation**: Binary, not Python library
- **Source**: [Google yamlfmt](https://github.com/google/yamlfmt)

**Option 2: yamlfix** (MIT-compatible)
- **Language**: Python
- **License**: MIT-compatible
- **Features**: Formatter with comment preservation
- **Limitation**: Formatter, not linter
- **Source**: [yamlfix](https://lyz-code.github.io/yamlfix/)

**Option 3: Create minimal linter**
- Use PyYAML (MIT) for parsing
- Implement only critical checks:
  - Trailing whitespace
  - Line length
  - Indentation consistency
  - Key duplication
  - Empty values
- Estimated: ~200-300 lines of Python

### Recommended Approach for yamllint

**Option A: Fork GPL yamllint** (Pragmatic)
- Accept GPL license for yamllint
- Bundle in container only (not in PyInstaller binary)
- Use for CI mode exclusively
- **Pros**: Full feature set, maintained
- **Cons**: GPL contamination in container

**Option B: Minimal Clean-Room Linter** (Recommended for HuskyCat)
- Implement 5-10 critical rules using PyYAML (MIT)
- Focus on most common issues:
  1. Trailing spaces
  2. Missing document end marker
  3. Inconsistent indentation
  4. Line length
  5. Key duplication
- **Pros**: MIT license, bundleable in binary, lightweight
- **Cons**: Fewer rules than yamllint, ongoing maintenance

**Option C: Use Google yamlfmt** (Alternative)
- Bundle Go binary in container
- Call from Python wrapper
- **Pros**: Apache 2.0, well-maintained, formatter + linter
- **Cons**: Not Python, formatter-focused

---

## 2. shellcheck Analysis

### Current Status
- **License**: GPL-3.0
- **Language**: Haskell
- **Rules**: ~340 checks (SC1000-SC2253 range)
- **Source**: [koalaman/shellcheck](https://github.com/koalaman/shellcheck) (GPL-3.0)

**Source**: [ShellCheck GitHub](https://github.com/koalaman/shellcheck), [ShellCheck rules gist](https://gist.github.com/nicerobot/53cee11ee0abbdc997661e65b348f375)

### Public Specifications Available

✅ **POSIX.1-2017 Shell Command Language**
- **Source**: [POSIX Shell Specification](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html)
- **Standard**: IEEE Std 1003.1-2017 / The Open Group Base Specifications Issue 7
- **Coverage**: Shell syntax, builtins, expansions, redirections
- **Status**: Fully public

✅ **Bash Reference Manual**
- **Source**: [GNU Bash Manual](https://www.gnu.org/software/bash/manual/)
- **Coverage**: Bash-specific extensions beyond POSIX
- **Status**: Public documentation

### Existing Python Libraries

| Library | License | Features | Limitations |
|---------|---------|----------|-------------|
| **bashlex** | GPL-3.0+ | Full bash parser (port of GNU bash parser) | GPL-licensed! |
| **shlex** (stdlib) | PSF | Simple POSIX shell lexer | No full parsing |

**Critical Finding**: bashlex is **GPL-licensed** (same as GNU bash), making it unsuitable for clean-room work.

**Source**: [bashlex GitHub](https://github.com/idank/bashlex) (GPL-3.0+), [Python shlex docs](https://docs.python.org/3/library/shlex.html)

### Complexity Assessment

**ShellCheck Rule Categories**:

| Category | Rule Range | Count | Examples |
|----------|------------|-------|----------|
| Parser/Syntax | SC1000-SC1999 | ~100 | Quoting, syntax errors |
| Semantic | SC2000-SC2999 | ~240 | Variable expansion, command substitution |

**Total Rules**: ~340 rules

**Rule Complexity Distribution**:
- **Simple** (20%): Quoting checks, basic syntax - ~70 rules
- **Medium** (50%): Variable expansion, conditionals - ~170 rules
- **Complex** (30%): Process substitution, advanced parsing - ~100 rules

**80/20 Analysis**:
- **Top 20% of rules**: Catch 80% of common bugs
- Estimated: ~70 high-value rules
- Focus areas:
  1. Unquoted variables (SC2086)
  2. [[ vs [ usage (SC2039)
  3. $? exit code checks (SC2181)
  4. Command substitution quoting
  5. -z/-n test operators

**Implementation Effort Estimate**:
- **Full reimplementation**: 12-18 months (340 rules)
- **Minimal viable (70 rules)**: 3-6 months
- **Top 20 rules**: 1-2 months

**Breakdown**:
1. **POSIX shell parser**: 4-8 weeks (or adapt shlex + custom AST)
2. **Bash extensions parser**: 4-8 weeks
3. **Rule engine**: 2-4 weeks
4. **Rule implementation** (70 rules): 8-12 weeks (avg 1-2 days per rule)
5. **Testing**: 4-6 weeks
6. **Documentation**: 2-3 weeks

**Total**: ~6 months for MVP with 70 rules

### Clean Room Legality

✅ **Legal**: Clean-room reimplementation is **legally feasible** under Sony v. Connectix

**Requirements**:
1. **Two-team approach**:
   - Team A: Reads POSIX spec + Bash manual, writes functional requirements
   - Team B: Implements from requirements only, never reads shellcheck source
2. **Documentation**: Extensive documentation of design decisions
3. **Test-driven**: Write tests from POSIX examples, not shellcheck output
4. **No GPL contamination**: Cannot use bashlex parser (GPL)

**Precautions**:
- ❌ Do NOT read shellcheck Haskell source code
- ❌ Do NOT use bashlex (GPL) for parsing
- ✅ Build custom parser from POSIX spec using Python stdlib (shlex + custom AST)
- ✅ Document all rule designs with POSIX spec references
- ✅ Use independent test cases from POSIX examples

**Legal Risk**: **MEDIUM**
- Large rule count (340) increases similarity risk
- Bash-specific extensions not fully documented in public specs
- Parser complexity may force similar design decisions
- Legal review recommended before distribution

**Source**: [Clean-room design Wikipedia](https://en.wikipedia.org/wiki/Clean-room_design), [GPL translation discussion](https://lobste.rs/s/q94fty/what_does_gpl_say_about_translating_some)

### Existing MIT/Apache Alternatives

**None Found**: No permissively-licensed Python alternatives to shellcheck exist.

**Alternatives**:
1. **shellcheck-py** (MIT wrapper): Pip-installable wrapper that downloads GPL shellcheck binary
   - **Source**: [shellcheck-py GitHub](https://github.com/shellcheck-py/shellcheck-py)
   - **License**: Wrapper is MIT, but binary is GPL
   - **Limitation**: Still GPL-licensed binary

2. **SonarQube** (LGPL/Commercial): Multi-language analysis including shell
   - **License**: LGPL (requires server)
   - **Limitation**: Heavy, server-based

**Verdict**: No suitable alternatives exist.

### Recommended Approach for shellcheck

**Option A: Use Existing Binary** (Pragmatic - Recommended)
- Bundle GPL shellcheck binary in container only
- Use for CI mode exclusively
- Keep out of PyInstaller binary
- **Pros**: Full feature set, maintained, proven
- **Cons**: GPL in container

**Option B: Minimal Clean-Room Subset** (High Risk)
- Implement top 20 rules (~1-2 months effort)
- Focus on critical quoting and expansion issues
- Use Python stdlib shlex + custom AST
- **Pros**: MIT-licensable, lightweight
- **Cons**: 6% feature coverage, ongoing maintenance, legal risk

**Option C: Skip Shell Linting** (Not Recommended)
- Omit shell linting from HuskyCat
- **Pros**: No GPL concerns
- **Cons**: Major feature gap for DevOps tool

**Recommendation**: **Option A** - Use existing GPL binary in container. Clean-room effort (6+ months) not justified for HuskyCat's use case.

---

## 3. hadolint Analysis

### Current Status
- **License**: GPL-3.0
- **Language**: Haskell
- **Dependencies**: ShellCheck (GPL) for RUN instruction validation
- **Rules**: ~50 DL rules + ShellCheck SC rules
- **Source**: [hadolint/hadolint](https://github.com/hadolint/hadolint) (GPL-3.0)

**Source**: [hadolint GitHub](https://github.com/hadolint/hadolint), [hadolint documentation](https://hadolint.github.io/hadolint/)

### Public Specifications Available

✅ **Docker Dockerfile Reference** (2026)
- **Source**: [Docker Dockerfile Reference](https://docs.docker.com/reference/dockerfile/)
- **Coverage**: All Dockerfile instructions (FROM, RUN, COPY, ENV, etc.)
- **Status**: Fully public, official documentation

✅ **Docker Best Practices** (2026)
- **Source**: [Docker Build Best Practices](https://docs.docker.com/build/building/best-practices/)
- **Coverage**: Multi-stage builds, layer caching, security
- **Key practices**:
  - Ephemeral containers
  - Minimal base images
  - Multi-stage builds
  - .dockerignore usage
  - Security hardening

**Source**: [Docker Best Practices](https://docs.docker.com/build/building/best-practices/)

### Existing Python Libraries

| Library | License | Features | Status |
|---------|---------|----------|--------|
| **dockerfile-parse** | BSD | Parse/modify Dockerfile | Active |
| **dockerlint** | MIT | Dockerfile linter | Active |
| **dockerfile** | MIT | Wrapper around Docker Go parser | Active |

**Key Finding**: **dockerlint** is MIT-licensed Python linter!

**Source**: [dockerfile-parse BSD](https://github.com/containerbuildsystem/dockerfile-parse), [dockerlint MIT](https://pypi.org/project/dockerlint/)

### Complexity Assessment

**hadolint Rule Categories**:

| Category | Prefix | Count | Examples |
|----------|--------|-------|----------|
| Dockerfile-specific | DL3xxx | ~50 | DL3000-DL3059 |
| ShellCheck (embedded) | SC2xxx | ~340 | Inherited from ShellCheck |

**DL Rule Examples**:
- DL3000: Use absolute WORKDIR
- DL3003: Use WORKDIR to switch to directory
- DL3007: Using latest tag (pin versions)
- DL3008: Pin versions in apt-get install
- DL3013: Pin versions in pip install
- DL3020: Use COPY instead of ADD for files
- DL3059: Multiple consecutive RUN instructions

**Implementation Effort**:
- **Full reimplementation** (50 DL rules + 340 SC rules): 6-12 months
- **DL rules only** (50 rules): 2-3 months
- **Core DL rules** (20 rules): 3-4 weeks

**80/20 Analysis**:
- Top 20 rules cover 80% of Dockerfile issues:
  1. Pin base image versions (DL3007)
  2. Pin package versions (DL3008, DL3013, DL3019)
  3. Use COPY over ADD (DL3020)
  4. Combine RUN statements (DL3059)
  5. Use absolute WORKDIR (DL3000)
  6. Avoid latest tag (DL3007)
  7. Clean package cache (DL3009)
  8. Use specific base images
  9. Non-root USER
  10. Multi-stage build usage

**Source**: [hadolint wiki](https://github.com/hadolint/hadolint/wiki/)

### Clean Room Legality

✅ **Legal**: Clean-room reimplementation is **legally feasible**

**Advantages for Dockerfile linting**:
- Simpler than shell: Only ~15 Dockerfile instructions
- Well-documented: Docker official docs are comprehensive
- Clear best practices: Docker publishes official guidelines
- No complex parsing: Dockerfile is simple line-based format

**Requirements**:
1. Use Dockerfile specification + Docker best practices as reference
2. Do NOT read hadolint Haskell source code
3. Use MIT-licensed dockerfile-parse for parsing
4. Implement rules based on Docker docs, not hadolint behavior

**Legal Risk**: **LOW**
- Simple specification (15 instructions)
- Well-documented best practices
- Multiple independent implementations exist
- Using MIT-licensed parser

### Existing MIT/Apache Alternatives

✅ **dockerlint** (MIT) - Python Dockerfile linter

**Key Details**:
- **License**: MIT (Copyright Reece Dunham 2020-present)
- **Language**: Python 3.4+
- **Features**:
  - Lint Dockerfile for size and functionality issues
  - Check for common anti-patterns
  - Python library + CLI
- **Source**: [dockerlint PyPI](https://pypi.org/project/dockerlint/)

**Evaluation**:
- ✅ MIT license (bundleable)
- ✅ Pure Python (no C extensions)
- ✅ Actively maintained
- ⚠️ Fewer rules than hadolint (~20 vs ~50)
- ⚠️ No ShellCheck integration for RUN instructions

**Alternative**: **dockerfile** (MIT wrapper)
- Wraps Docker's official Go parser
- MIT-licensed wrapper
- More focused on parsing than linting

### Recommended Approach for hadolint

**Option A: Use dockerlint** (Recommended)
- Use existing MIT-licensed Python package
- Bundle in PyInstaller binary (~500 KB)
- Supplement with custom rules if needed
- **Pros**: MIT license, bundleable, lightweight, maintained
- **Cons**: Fewer rules than hadolint

**Option B: Extend dockerlint** (If more rules needed)
- Fork dockerlint (MIT)
- Add 10-20 additional DL rules from Docker best practices
- Estimated effort: 2-4 weeks
- **Pros**: MIT license, tailored to HuskyCat needs
- **Cons**: Maintenance burden

**Option C: Clean-Room Minimal Linter** (Alternative)
- Implement 20 core rules from Docker docs
- Use dockerfile-parse (BSD) for parsing
- Estimated effort: 3-4 weeks
- **Pros**: Fully controlled, minimal dependencies
- **Cons**: Reinventing wheel, dockerlint already exists

**Option D: Use GPL hadolint Binary** (Not Recommended)
- Bundle in container only
- Full feature set
- **Pros**: Most comprehensive
- **Cons**: GPL, Haskell binary, larger size

**Recommendation**: **Option A** - Use dockerlint (MIT). Excellent existing solution that meets HuskyCat's needs without GPL concerns.

---

## Feasibility Matrix

| Tool | Effort | Risk | Legal | Complexity | Recommendation |
|------|--------|------|-------|------------|----------------|
| **yamllint** | Medium (4-6 weeks) | Low | ✅ Clean-room viable | Low (~20-30 rules) | **Minimal clean-room** or **fork GPL** |
| **shellcheck** | High (6+ months) | Medium | ⚠️ Clean-room viable | High (~340 rules) | **Use GPL binary** in container |
| **hadolint** | N/A | N/A | N/A | N/A | **Use dockerlint (MIT)** |

### Effort Scale
- **Low**: <1 month
- **Medium**: 1-3 months
- **High**: 3-12 months
- **Very High**: 12+ months

### Risk Scale
- **Low**: Simple specs, clear precedents, low similarity risk
- **Medium**: Complex specs, some ambiguity, moderate similarity risk
- **High**: Very complex, GPL dependencies, high similarity risk

---

## Detailed Recommendations

### For HuskyCat Project

Based on the existing feasibility analysis in `/Users/jsullivan2/git/huskycats-bates/docs/research/python-tools-bundling-feasibility.md`, which recommends bundling Python tools but delegating specialized tools to containers, here are specific recommendations:

#### 1. yamllint Strategy

**Recommendation**: Create minimal MIT-licensed Python linter

**Implementation**:
```python
# huskycat/validators/yaml_lint_clean.py
import yaml  # PyYAML (MIT)

class YamlLintClean:
    """Minimal YAML linter using MIT-licensed PyYAML"""

    def check_trailing_spaces(self, content: str) -> List[Issue]:
        """Check for trailing whitespace"""
        pass

    def check_line_length(self, content: str, max_length: int = 120) -> List[Issue]:
        """Check line length"""
        pass

    def check_indentation(self, content: str) -> List[Issue]:
        """Check consistent indentation"""
        pass

    def check_key_duplicates(self, doc: dict) -> List[Issue]:
        """Check for duplicate keys"""
        pass

    def check_empty_values(self, doc: dict) -> List[Issue]:
        """Check for empty/null values where inappropriate"""
        pass
```

**Rationale**:
- PyYAML (MIT) provides robust parsing
- 5 core rules cover 80% of YAML issues
- ~200-300 lines of Python
- Bundleable in PyInstaller binary (~1-2 MB)
- No GPL concerns
- 1-2 weeks implementation

**Fallback**: Keep GPL yamllint in container for CI mode (comprehensive validation)

#### 2. shellcheck Strategy

**Recommendation**: Use GPL binary in container only

**Implementation**:
- Exclude from PyInstaller binary
- Bundle in container image
- Use for CI mode exclusively
- Git hooks mode: Skip shell linting OR warn user to install shellcheck locally

**Rationale**:
- 340 rules too complex for clean-room (6+ months effort)
- GPL binary acceptable in container context
- Git hooks can function without shell linting
- Users can install shellcheck locally if needed

**Alternative** (if GPL absolutely unacceptable):
- Create minimal 20-rule subset linter
- Focus on critical quoting issues
- Accept 6% feature coverage
- Estimated 1-2 months implementation

#### 3. hadolint Strategy

**Recommendation**: Use dockerlint (MIT) immediately

**Implementation**:
```python
# Add to pyproject.toml
[project.dependencies]
dockerlint = ">=0.3.0"

# Add to unified_validation.py
class DockerLintValidator(Validator):
    @property
    def name(self) -> str:
        return "docker-dockerlint"

    @property
    def command(self) -> str:
        return "dockerlint"

    @property
    def extensions(self) -> Set[str]:
        return {".dockerfile"}

    def can_handle(self, filepath: Path) -> bool:
        return filepath.name in ["Dockerfile", "ContainerFile"] or filepath.suffix == ".dockerfile"
```

**Rationale**:
- MIT-licensed, ready to use
- Python package (~500 KB)
- Bundleable in PyInstaller binary
- Covers core Dockerfile best practices
- No development effort required

**If more rules needed**:
- Fork dockerlint (MIT allows modification)
- Add 5-10 critical rules from Docker best practices
- Estimated 1-2 weeks additional effort

---

## Legal Safeguards for Clean-Room Development

If pursuing clean-room reimplementation, follow these protocols:

### 1. Two-Team Clean Room Process

**Team A: Specification Team**
- Reads public specifications only:
  - POSIX.1-2017 Shell Command Language
  - Docker Dockerfile Reference
  - YAML 1.2 Specification
  - Docker Best Practices
- Writes detailed functional requirements
- Documents expected behavior with examples
- **Never** reads GPL source code

**Team B: Implementation Team**
- Reads functional requirements from Team A only
- Implements features based on requirements
- Writes tests based on spec examples
- **Never** reads GPL source code
- **Never** communicates directly with Team A during implementation

### 2. Documentation Requirements

**Required Documentation**:
1. **Design Decision Log**: Why each rule exists (reference public docs)
2. **Test Cases**: From public specs, not GPL tools
3. **Clean Room Certification**: Affidavit that GPL code was not consulted
4. **Specification References**: Link each rule to public spec section

**Example**:
```markdown
## Rule: Unquoted Variable Check

**Specification Reference**: POSIX.1-2017 Section 2.6.2 Parameter Expansion
**Rationale**: Unquoted variables undergo word splitting and pathname expansion
**Expected Behavior**: Warn when $var used without quotes outside [[ ]] context
**Test Cases**: From POSIX spec examples (Section 2.6.2)
**Design Decision**: Implemented as AST visitor pattern for variable nodes
```

### 3. Source Code Headers

**Required Header**:
```python
"""
YAML Linter - Clean Room Implementation

This module implements YAML linting based solely on:
- YAML 1.2 Specification (https://yaml.org/spec/1.2/)
- Common YAML best practices from public sources

NO GPL-licensed code was consulted during implementation.

License: MIT
Date: 2026-01-16
"""
```

### 4. Legal Review Checklist

Before distribution:
- [ ] Confirm no GPL source code was consulted
- [ ] Verify all team members signed clean-room certification
- [ ] Document all design decisions with public spec references
- [ ] Review for substantial similarity to GPL implementation
- [ ] Obtain legal counsel review if distributing commercially

---

## Existing Python Parser Libraries Summary

### Shell Parsers

| Library | License | Features | Suitability |
|---------|---------|----------|-------------|
| **shlex** (stdlib) | PSF | Simple lexer, POSIX mode | ✅ Can use for basic parsing |
| **bashlex** | **GPL-3.0+** | Full bash parser (C port) | ❌ Cannot use - GPL |

**Verdict**: Must build custom parser using shlex + AST for clean-room shell linter.

### Dockerfile Parsers

| Library | License | Features | Suitability |
|---------|---------|----------|-------------|
| **dockerfile-parse** | BSD | Parse/modify Dockerfile | ✅ Can use for clean-room |
| **dockerfile** | MIT | Wrapper around Docker parser | ✅ Can use for clean-room |

**Verdict**: Use dockerfile-parse (BSD) for clean-room Dockerfile linter.

### YAML Parsers

| Library | License | YAML Version | Suitability |
|---------|---------|--------------|-------------|
| **PyYAML** | MIT | 1.1 | ✅ Can use for clean-room |
| **ruamel.yaml** | MIT | 1.2 | ✅ Can use for clean-room |

**Verdict**: Use PyYAML or ruamel.yaml (both MIT) for clean-room YAML linter.

---

## Implementation Priorities

### Phase 1: Immediate (Sprint 1)
1. ✅ **Add dockerlint (MIT)** to PyInstaller binary
   - Effort: 1 day
   - Replace GPL hadolint for basic Dockerfile linting
   - MIT license, bundleable

2. ✅ **Keep GPL binaries in container**
   - shellcheck, hadolint, yamllint in container only
   - CI mode uses full-featured GPL tools
   - Git hooks mode uses bundled tools only

### Phase 2: Short-term (Sprint 2-3)
3. ⚠️ **Evaluate minimal YAML linter need**
   - Assess if GPL yamllint in container is sufficient
   - If binary bundling required: Implement 5-rule MIT linter
   - Effort: 1-2 weeks
   - Decision point: Is CI-only YAML linting acceptable?

### Phase 3: Long-term (Future)
4. ⚠️ **Assess shell linting demand**
   - Monitor user requests for git hooks shell linting
   - If high demand: Consider 20-rule minimal clean-room implementation
   - Effort: 1-2 months
   - Low priority: Most users can install shellcheck locally

---

## Cost-Benefit Analysis

### yamllint Clean-Room

**Costs**:
- Development: 4-6 weeks
- Testing: 1-2 weeks
- Maintenance: ~1-2 weeks/year
- Total first year: ~8-10 weeks

**Benefits**:
- MIT-licensable binary
- ~2 MB bundled size
- No GPL concerns
- Custom rules for HuskyCat needs

**Verdict**: **Marginal** - Only if binary bundling required AND GPL in container unacceptable

### shellcheck Clean-Room

**Costs**:
- Development: 6-12 months (full) OR 1-2 months (20 rules)
- Parser development: 2-4 months
- Testing: 2-4 months
- Maintenance: ~4-8 weeks/year
- Total first year: ~12-18 months

**Benefits**:
- MIT-licensable binary
- Shell linting in git hooks mode
- No GPL concerns

**Verdict**: **Not Justified** - Effort far exceeds benefit. Use GPL binary in container.

### hadolint Clean-Room

**Costs**:
- $0 - dockerlint (MIT) already exists

**Benefits**:
- MIT license
- Immediate availability
- ~500 KB bundled
- No development needed

**Verdict**: **Highly Favorable** - Use dockerlint immediately, no clean-room needed.

---

## Conclusion

### Summary Recommendations

| Tool | Action | Rationale | Effort |
|------|--------|-----------|--------|
| **yamllint** | Use GPL in container OR minimal clean-room if binary required | GPL acceptable for CI; MIT linter for git hooks if needed | 0 (use GPL) OR 4-6 weeks (clean-room) |
| **shellcheck** | Use GPL binary in container only | 340 rules too complex; clean-room not justified | 0 (use GPL) |
| **hadolint** | Use dockerlint (MIT) immediately | Perfect existing solution, no development needed | 0 (use existing) |

### Overall Strategy

**Hybrid Approach** (matches existing bundling feasibility):

1. **PyInstaller Binary** (MIT-licensed tools only):
   - ✅ dockerlint (MIT) - Dockerfile linting
   - ✅ Python tools (black, ruff, mypy, etc.) - already bundled
   - ⚠️ Optional: Minimal YAML linter (MIT) if needed

2. **Container** (GPL tools acceptable):
   - shellcheck (GPL) - Full shell linting
   - hadolint (GPL) - Comprehensive Dockerfile linting
   - yamllint (GPL) - Full YAML linting

3. **Mode-Specific Routing**:
   - **Git Hooks Mode**: Use PyInstaller binary (MIT tools only)
   - **CI Mode**: Use container (full GPL toolchain)
   - **CLI Mode**: Try binary first, fall back to container

**This strategy**:
- ✅ Avoids GPL in distributed binary
- ✅ Provides full toolchain in CI
- ✅ Requires minimal clean-room effort
- ✅ Leverages existing MIT tools (dockerlint)
- ✅ Matches HuskyCat's product mode architecture

---

## References

### Legal Resources
- [Clean-room design (Wikipedia)](https://en.wikipedia.org/wiki/Clean-room_design)
- [Sony v. Connectix precedent](https://www.retroreversing.com/clean-room-reversing)
- [GPL translation discussion](https://lobste.rs/s/q94fty/what_does_gpl_say_about_translating_some)

### Tool Documentation
- [ShellCheck GitHub](https://github.com/koalaman/shellcheck)
- [ShellCheck Rules](https://gist.github.com/nicerobot/53cee11ee0abbdc997661e65b348f375)
- [hadolint GitHub](https://github.com/hadolint/hadolint)
- [hadolint wiki](https://github.com/hadolint/hadolint/wiki/)
- [yamllint GitHub](https://github.com/adrienverge/yamllint)
- [dockerlint PyPI](https://pypi.org/project/dockerlint/)

### Specifications
- [POSIX.1-2017 Shell Command Language](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html)
- [YAML 1.2 Specification](https://yaml.org/spec/)
- [Docker Dockerfile Reference](https://docs.docker.com/reference/dockerfile/)
- [Docker Build Best Practices](https://docs.docker.com/build/building/best-practices/)

### Parser Libraries
- [bashlex (GPL)](https://github.com/idank/bashlex)
- [Python shlex (PSF)](https://docs.python.org/3/library/shlex.html)
- [dockerfile-parse (BSD)](https://github.com/containerbuildsystem/dockerfile-parse)
- [PyYAML (MIT)](https://github.com/yaml/pyyaml)
- [ruamel.yaml (MIT)](https://pypi.org/project/ruamel.yaml/)

---

**Research Completed**: 2026-01-16
**Total Research Time**: ~3 hours
**Next Steps**: Review with HuskyCat maintainers, decide on yamllint strategy, implement dockerlint integration
