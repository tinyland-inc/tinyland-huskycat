# GitLab CI Validation

HuskyCats Bates now includes official GitLab CI schema validation, using the same JSON schema that powers GitLab's Pipeline Editor.

## 🚀 How It Works

The validation uses:
1. **Official GitLab CI JSON Schema** from `gitlab.com/gitlab-org/gitlab`
2. **JSON Schema Draft-07** validation
3. **Python jsonschema** library for validation
4. **Automatic schema caching** to avoid repeated downloads

## 📋 What Gets Validated

The GitLab CI validator checks:
- ✅ **Job definitions** - Ensures jobs have valid structure
- ✅ **Script syntax** - Validates that scripts are strings or arrays (catches the "nested array" error!)
- ✅ **Stage references** - Ensures jobs reference defined stages
- ✅ **Keyword usage** - Validates all GitLab CI keywords
- ✅ **Include syntax** - Checks include statements
- ✅ **Variables** - Validates variable definitions
- ✅ **Rules and conditions** - Ensures proper rule syntax

## 🔧 Usage

### Automatic Validation

The comprehensive lint automatically runs GitLab CI validation when you commit changes:

```bash
# Stage your .gitlab-ci.yml changes
git add .gitlab-ci.yml

# Commit - validation runs automatically
git commit -m "ci: update pipeline configuration"
```

### Manual Validation

You can run the validator directly:

```bash
# Validate all GitLab CI files
./scripts/validate-gitlab-ci-schema.py

# Or through comprehensive lint
./scripts/comprehensive-lint.sh --all
```

### In Docker/Podman Container

```bash
# Using the published image (auto-detects architecture)
podman run --rm -v "$(pwd):/workspace" -w /workspace \
  --entrypoint /bin/bash \
  registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest \
  -c "python3 scripts/validate-gitlab-ci-schema.py"

# Or with docker
docker run --rm -v "$(pwd):/workspace" -w /workspace \
  --entrypoint /bin/bash \
  registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest \
  -c "python3 scripts/validate-gitlab-ci-schema.py"
```

### Testing the Validation

To test that the validation is working correctly:

1. **Create a test file with errors**:
```yaml
# test-ci-error.yml
stages:
  - test

test:job:
  stage: test
  # This script format is invalid
  script:
    command: "echo test"
    another: "echo another"
  
bad:job:
  invalid_keyword: true  # This keyword doesn't exist
  script:
    - echo "test"
```

2. **Run the validator**:
```bash
# Direct validation
python3 scripts/validate-gitlab-ci-schema.py

# Or in container
podman run --rm -v "$(pwd):/workspace" -w /workspace \
  --entrypoint python3 \
  registry.gitlab.com/bates-ils/projects/trustees-portal/sid-controller/huskycats-bates/husky-lint:latest \
  /workspace/scripts/validate-gitlab-ci-schema.py
```

3. **Expected output**:
```
❌ test-ci-error.yml has 2 validation error(s):
  1. {'command': 'echo test', 'another': 'echo another'} is not valid under any of the given schemas
     Path: test:job -> script
  2. Additional properties are not allowed ('invalid_keyword' was unexpected)
     Path: bad:job
```

## 📊 Example Output

### Valid Configuration
```
ℹ️  Using cached GitLab CI schema
ℹ️  Found 2 GitLab CI file(s)
✅ .gitlab-ci.yml is valid according to GitLab CI schema
✅ .gitlab/ci/deploy.yml is valid according to GitLab CI schema
```

### Invalid Configuration
```
ℹ️  Using cached GitLab CI schema
ℹ️  Found 1 GitLab CI file(s)
❌ .gitlab-ci.yml has 2 validation error(s):
  1. 'script' must be array
     Path: jobs -> test -> script
  2. Additional properties are not allowed ('befor_script' was unexpected)
     Path: jobs -> build
```

## 🔍 Common Errors Caught

1. **Script must be array** - The error you encountered!
   ```yaml
   # ❌ Invalid - script with nested arrays
   script:
     - |
       echo "test"
       
   # ✅ Valid - flat array
   script:
     - echo "test"
     - echo "another command"
   ```

2. **Invalid job names**
   ```yaml
   # ❌ Invalid - job names can't start with .
   .build:
     script: echo "test"
   
   # ✅ Valid
   build:
     script: echo "test"
   ```

3. **Unknown keywords**
   ```yaml
   # ❌ Invalid - typo in keyword
   befor_script:
     - echo "setup"
   
   # ✅ Valid
   before_script:
     - echo "setup"
   ```

## 🛠️ Technical Details

### Schema Location
The official GitLab CI schema is fetched from:
```
https://gitlab.com/gitlab-org/gitlab/-/raw/master/app/assets/javascripts/editor/schema/ci.json
```

### Caching
The schema is cached locally at:
```
~/.cache/huskycats/gitlab-ci-schema.json
```

The cache is refreshed every 7 days to ensure you have the latest validation rules.

### Python Dependencies
The validator requires:
- `jsonschema>=4.23.0` - JSON Schema validation
- `pyyaml>=6.0.2` - YAML parsing

These are pre-installed in the HuskyCats Bates container.

## 🚨 Limitations

While this validation catches most GitLab CI syntax errors, some limitations exist:

1. **Dynamic includes** - Can't validate files included with variables
2. **External files** - Can't validate remote includes
3. **Runtime behavior** - Can't validate if jobs will actually work

For complete validation, always test in a merge request pipeline.

## 🔗 References

- [GitLab CI/CD YAML syntax reference](https://docs.gitlab.com/ci/yaml/)
- [GitLab CI/CD Schema Development](https://docs.gitlab.com/ee/development/cicd/schema.html)
- [JSON Schema Draft-07](https://json-schema.org/draft-07/json-schema-release-notes.html)