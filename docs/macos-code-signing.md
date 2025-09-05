# macOS Code Signing for HuskyCat Binaries

This guide covers setting up code signing for macOS binaries in GitLab CI/CD pipelines using PyInstaller.

## Overview

HuskyCat supports automatic code signing for macOS binaries using Apple Developer certificates. This ensures:

- **Gatekeeper Compatibility**: Binaries run without security warnings
- **Hardened Runtime**: Enhanced security with proper entitlements
- **Universal Binaries**: Support for both Intel and Apple Silicon Macs
- **CI/CD Integration**: Automated signing in GitLab pipelines

## Prerequisites

### 1. Apple Developer Account

You need an Apple Developer account with:
- **Developer ID Application Certificate**: For distributing outside the Mac App Store
- **Team ID**: Your Apple Developer Team identifier

### 2. Certificate Export

1. **Open Keychain Access** on a Mac with your signing certificate
2. **Find your certificate**: "Developer ID Application: Your Name (TEAM_ID)"
3. **Export as P12**: Right-click → Export → `.p12` format
4. **Set a password**: Choose a secure password for the .p12 file

### 3. GitLab Runner Setup

You need a GitLab Runner on macOS with:
- **Xcode Command Line Tools**: `xcode-select --install`
- **Python 3.11+**: For UV and PyInstaller
- **Runner Tag**: `macos` (configured in `.gitlab-ci.yml`)

## GitLab CI/CD Variables Setup

Configure these variables in your GitLab project's CI/CD settings:

### Required Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `APPLE_SIGNING_IDENTITY` | Variable | Full certificate name | `"Developer ID Application: Your Name (ABCD123456)"` |
| `APPLE_TEAM_ID` | Variable | Apple Developer Team ID | `ABCD123456` |
| `APPLE_CERTIFICATE_P12_BASE64` | Variable (Masked) | Base64-encoded .p12 certificate | `MIIK...` |
| `APPLE_CERTIFICATE_PASSWORD` | Variable (Masked) | Password for .p12 certificate | `your-cert-password` |
| `KEYCHAIN_PASSWORD` | Variable (Masked) | Temporary keychain password | `ci-keychain-pass` |

### Encoding Your Certificate

```bash
# Convert .p12 to base64 for GitLab variable
base64 -i your-certificate.p12 | pbcopy
```

## Local Development

### Building Signed Binaries Locally

```bash
# Set your signing identity
export APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name (TEAM_ID)"

# Build signed binary with entitlements
npm run build:binary:signed

# Or use the build script directly
uv run python build_binary.py \
  --codesign-identity "$APPLE_SIGNING_IDENTITY" \
  --entitlements-file entitlements.plist \
  --target-arch universal2 \
  --skip-upx
```

### Testing Unsigned Binaries

```bash
# Build without signing (for testing)
npm run build:binary -- --skip-upx --target-arch universal2

# Test the binary
./dist/huskycat --version
```

## Entitlements Configuration

The `entitlements.plist` file defines permissions for the signed binary:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Allow executing binaries and scripts -->
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    
    <!-- Allow loading of arbitrary libraries -->
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    
    <!-- Allow network access for downloading schemas -->
    <key>com.apple.security.network.client</key>
    <true/>
    
    <!-- Allow file system access for validation tools -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    
    <!-- Required for PyInstaller binaries -->
    <key>com.apple.security.cs.disable-executable-page-protection</key>
    <true/>
    
    <!-- Allow runtime code execution (Python bytecode) -->
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
</dict>
</plist>
```

### Key Entitlements Explained

- **`allow-unsigned-executable-memory`**: Allows PyInstaller to execute Python bytecode
- **`disable-library-validation`**: Permits loading of validation tool libraries  
- **`network.client`**: Enables downloading of validation schemas
- **`files.user-selected.read-write`**: Allows validation of user files
- **`disable-executable-page-protection`**: Required for PyInstaller executables

## GitLab CI Pipeline

The macOS build job in `.gitlab-ci.yml`:

```yaml
binary:build:macos:
  stage: package
  tags: 
    - macos  # Requires macOS runner
  variables:
    APPLE_SIGNING_IDENTITY: $APPLE_SIGNING_IDENTITY
    APPLE_TEAM_ID: $APPLE_TEAM_ID
  before_script:
    # Setup Python environment
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.local/bin:$PATH"
    - uv sync --extra build
    
    # Import signing certificate
    - |
      if [ -n "$APPLE_CERTIFICATE_P12_BASE64" ]; then
        echo "🔐 Importing signing certificate..."
        echo "$APPLE_CERTIFICATE_P12_BASE64" | base64 -D > certificate.p12
        security create-keychain -p "$KEYCHAIN_PASSWORD" ci.keychain
        security import certificate.p12 -k ci.keychain -P "$APPLE_CERTIFICATE_PASSWORD" -A
        rm certificate.p12
      fi
  script:
    # Build signed binary
    - |
      uv run python build_binary.py \
        --codesign-identity "$APPLE_SIGNING_IDENTITY" \
        --entitlements-file entitlements.plist \
        --target-arch universal2 \
        --skip-upx
```

## Verification Commands

### Check Code Signing Status

```bash
# Verify signature
codesign -dv dist/huskycat

# Check entitlements
codesign -d --entitlements - dist/huskycat

# Test Gatekeeper compatibility
spctl -a -t exec -vv dist/huskycat
```

### Binary Architecture

```bash
# Check universal binary
file dist/huskycat
# Output: Mach-O universal binary with 2 architectures: [x86_64:Mach-O 64-bit executable x86_64] [arm64:Mach-O 64-bit executable arm64]

# Test on different architectures
arch -x86_64 ./dist/huskycat --version  # Intel
arch -arm64 ./dist/huskycat --version   # Apple Silicon
```

## Troubleshooting

### Common Issues

#### 1. "Binary Killed by macOS"

**Cause**: Unsigned binary with hardened runtime
**Solution**: Either sign the binary or build without UPX compression

```bash
# Rebuild without UPX
npm run build:binary -- --skip-upx
```

#### 2. "Code Sign Error: Identity Not Found"

**Cause**: Certificate not properly imported
**Solution**: Verify certificate installation

```bash
security find-identity -v -p codesigning
```

#### 3. "Gatekeeper Blocks Binary"

**Cause**: Invalid signature or entitlements
**Solution**: Check signature and entitlements

```bash
codesign -dv dist/huskycat
codesign --verify --verbose dist/huskycat
```

#### 4. "PyInstaller Import Errors"

**Cause**: Missing entitlements for dynamic loading
**Solution**: Ensure entitlements include:
- `com.apple.security.cs.disable-library-validation`
- `com.apple.security.cs.allow-unsigned-executable-memory`

### Debug Mode

Build with verbose signing output:

```bash
uv run python build_binary.py \
  --codesign-identity "$APPLE_SIGNING_IDENTITY" \
  --entitlements-file entitlements.plist \
  --target-arch universal2 \
  --skip-upx \
  --verbose
```

## Security Considerations

### Certificate Security

- **Never commit certificates**: Use GitLab CI/CD variables (masked)
- **Rotate regularly**: Update certificates before expiration
- **Limit access**: Restrict who can modify CI/CD variables
- **Temporary keychains**: Always clean up in CI `after_script`

### Entitlements

- **Minimal permissions**: Only include required entitlements
- **Regular review**: Audit entitlements for security implications
- **Testing**: Verify binary works with minimal entitlements

### Distribution

- **Notarization**: Consider Apple notarization for additional trust
- **Checksums**: Provide SHA256 checksums for distributed binaries
- **HTTPS only**: Distribute binaries over secure channels

## Resources

- [Apple Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/)
- [PyInstaller macOS Guide](https://pyinstaller.org/en/stable/feature-notes.html#macos-support)
- [GitLab CI macOS Runners](https://docs.gitlab.com/ee/ci/runners/hosted_runners/macos/)
- [Hardened Runtime Entitlements](https://developer.apple.com/documentation/security/hardened_runtime)