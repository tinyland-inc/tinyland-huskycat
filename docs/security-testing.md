# HuskyCats MCP Server Security Testing Framework

## Overview

This document outlines the comprehensive security testing framework for the HuskyCats MCP Server v2.0.0, covering infrastructure security, container security, network protections, and Kubernetes deployment validation.

## 🛡️ Security Testing Domains

### 1. Infrastructure Security Testing
- fail2ban configuration validation
- firewalld rules verification
- SSH hardening enforcement
- System service security

### 2. Network Security Testing
- RPC/HTTP transport security
- Authentication mechanism validation
- CORS policy enforcement
- Rate limiting and DDoS protection

### 3. Container Security Testing
- Non-root execution validation
- Filesystem permissions
- Resource limits enforcement
- Security context validation

### 4. Kubernetes Security Testing
- Pod security standards
- RBAC configuration
- Network policies
- Horizontal scaling security

### 5. Filesystem Sync Security
- Syncthing configuration validation
- Access control mechanisms
- Data integrity verification
- Unauthorized access prevention

---

## 🔧 Test Implementation Framework

### Core Testing Libraries

```bash
# Install testing dependencies
npm install --save-dev \
  @types/jest \
  jest \
  supertest \
  dockerode \
  kubernetes-client \
  ssh2 \
  node-nmap \
  @types/supertest
```

### Test Structure

```
tests/
├── security/
│   ├── infrastructure/
│   │   ├── fail2ban.test.ts
│   │   ├── firewalld.test.ts
│   │   ├── ssh-hardening.test.ts
│   │   └── systemd.test.ts
│   ├── network/
│   │   ├── transport-security.test.ts
│   │   ├── authentication.test.ts
│   │   ├── cors.test.ts
│   │   └── rate-limiting.test.ts
│   ├── container/
│   │   ├── user-privileges.test.ts
│   │   ├── filesystem.test.ts
│   │   ├── resources.test.ts
│   │   └── security-context.test.ts
│   ├── kubernetes/
│   │   ├── pod-security.test.ts
│   │   ├── rbac.test.ts
│   │   ├── network-policies.test.ts
│   │   └── hpa-security.test.ts
│   └── syncthing/
│       ├── config-validation.test.ts
│       ├── access-control.test.ts
│       ├── data-integrity.test.ts
│       └── unauthorized-access.test.ts
├── integration/
│   ├── podman-desktop.test.ts
│   ├── k8s-scaling.test.ts
│   └── end-to-end.test.ts
└── utils/
    ├── security-helpers.ts
    ├── container-utils.ts
    └── k8s-utils.ts
```

---

## 🔒 Infrastructure Security Tests

### fail2ban Configuration Validation

```typescript
// tests/security/infrastructure/fail2ban.test.ts
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';

const execAsync = promisify(exec);

describe('fail2ban Security Tests', () => {
  describe('Configuration Validation', () => {
    test('should have mcp-server jail configured', async () => {
      const config = await fs.readFile('/etc/fail2ban/jail.d/mcp-server.conf', 'utf8');
      
      expect(config).toContain('[mcp-server]');
      expect(config).toContain('enabled = true');
      expect(config).toContain('port = 8080');
      expect(config).toContain('maxretry = 5');
      expect(config).toContain('bantime = 3600');
    });

    test('should have correct filter patterns', async () => {
      const config = await fs.readFile('/etc/fail2ban/jail.d/mcp-server.conf', 'utf8');
      
      expect(config).toContain('failregex = .*MCP Server.*Unauthorized.*from <HOST>.*');
      expect(config).toContain('.*MCP Server.*Invalid request.*from <HOST>.*');
      expect(config).toContain('.*MCP Server.*Parse error.*from <HOST>.*');
    });

    test('should detect brute force attempts', async () => {
      // Simulate failed authentication attempts
      const attempts = Array(6).fill(0).map(() => 
        fetch('http://localhost:8080/rpc', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer invalid-token' },
          body: JSON.stringify({ method: 'initialize' })
        }).catch(() => {}) // Ignore errors
      );

      await Promise.all(attempts);
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Check if IP is banned
      const { stdout } = await execAsync('fail2ban-client status mcp-server');
      expect(stdout).toContain('Currently banned');
    });
  });

  describe('Runtime Protection', () => {
    test('should ban IP after maxretry attempts', async () => {
      const clientIP = '192.168.1.100';
      
      // Simulate multiple failed attempts from specific IP
      for (let i = 0; i < 6; i++) {
        await simulateFailedRequest(clientIP);
      }

      const bannedIPs = await getBannedIPs('mcp-server');
      expect(bannedIPs).toContain(clientIP);
    });

    test('should unban IP after bantime expires', async () => {
      // This would be a longer integration test
      // Mock time or use shorter bantime for testing
    });
  });
});
```

### firewalld Rules Verification

```typescript
// tests/security/infrastructure/firewalld.test.ts
describe('firewalld Security Tests', () => {
  describe('Port Configuration', () => {
    test('should only allow required ports', async () => {
      const { stdout } = await execAsync('firewall-cmd --list-ports');
      const allowedPorts = stdout.split(' ');
      
      expect(allowedPorts).toContain('8080/tcp');  // MCP Server
      expect(allowedPorts).toContain('8384/tcp');  // Syncthing GUI
      expect(allowedPorts).toContain('22000/tcp'); // Syncthing sync
      expect(allowedPorts).toContain('21027/udp'); // Syncthing discovery
      
      // Should not contain dangerous ports
      expect(allowedPorts).not.toContain('22/tcp');   // SSH
      expect(allowedPorts).not.toContain('3306/tcp'); // MySQL
      expect(allowedPorts).not.toContain('5432/tcp'); // PostgreSQL
    });

    test('should have strict source restrictions', async () => {
      const { stdout } = await execAsync('firewall-cmd --list-rich-rules');
      
      // Check for source IP restrictions if configured
      if (process.env.ALLOWED_NETWORKS) {
        expect(stdout).toContain('source address');
      }
    });
  });

  describe('Service Configuration', () => {
    test('should have firewalld service active', async () => {
      const { stdout } = await execAsync('systemctl is-active firewalld');
      expect(stdout.trim()).toBe('active');
    });

    test('should have proper zone configuration', async () => {
      const { stdout } = await execAsync('firewall-cmd --get-default-zone');
      expect(stdout.trim()).toBe('public');
    });
  });
});
```

### SSH Hardening Validation

```typescript
// tests/security/infrastructure/ssh-hardening.test.ts
describe('SSH Hardening Tests', () => {
  describe('Configuration Validation', () => {
    test('should disable password authentication', async () => {
      const config = await fs.readFile('/etc/ssh/sshd_config', 'utf8');
      
      expect(config).toMatch(/^PasswordAuthentication\s+no$/m);
      expect(config).toMatch(/^ChallengeResponseAuthentication\s+no$/m);
      expect(config).toMatch(/^UsePAM\s+no$/m);
    });

    test('should enforce key-based authentication only', async () => {
      const config = await fs.readFile('/etc/ssh/sshd_config', 'utf8');
      
      expect(config).toMatch(/^PubkeyAuthentication\s+yes$/m);
      expect(config).toMatch(/^AuthorizedKeysFile\s+\.ssh\/authorized_keys$/m);
    });

    test('should disable root login', async () => {
      const config = await fs.readFile('/etc/ssh/sshd_config', 'utf8');
      expect(config).toMatch(/^PermitRootLogin\s+no$/m);
    });

    test('should have secure ciphers and MACs', async () => {
      const config = await fs.readFile('/etc/ssh/sshd_config', 'utf8');
      
      expect(config).toContain('Ciphers chacha20-poly1305@openssh.com');
      expect(config).toContain('MACs hmac-sha2-256-etm@openssh.com');
    });
  });

  describe('Connection Testing', () => {
    test('should reject password authentication attempts', async () => {
      // This would require SSH client testing
      // Could use ssh2 library to test connection attempts
    });
  });
});
```

---

## 🌐 Network Security Tests

### RPC/HTTP Transport Security

```typescript
// tests/security/network/transport-security.test.ts
import request from 'supertest';
import { createServer } from '../../../src/server';

describe('Transport Security Tests', () => {
  let server: any;

  beforeAll(() => {
    server = createServer();
  });

  describe('HTTPS Enforcement', () => {
    test('should set security headers', async () => {
      const response = await request(server)
        .get('/health')
        .expect(200);

      expect(response.headers['x-content-type-options']).toBe('nosniff');
      expect(response.headers['x-frame-options']).toBe('DENY');
      expect(response.headers['x-xss-protection']).toBe('1; mode=block');
      expect(response.headers['strict-transport-security']).toContain('max-age=31536000');
      expect(response.headers['content-security-policy']).toBe("default-src 'none'");
    });

    test('should enforce secure content types', async () => {
      const response = await request(server)
        .post('/rpc')
        .send({ method: 'initialize' })
        .expect(401);

      expect(response.headers['content-type']).toContain('application/json');
    });
  });

  describe('TLS Configuration', () => {
    test('should use strong TLS ciphers', async () => {
      // Test TLS cipher suites if HTTPS is enabled
      if (process.env.HTTPS_ENABLED === 'true') {
        const tlsInfo = await getTLSInfo('localhost', 8080);
        expect(tlsInfo.cipher).toMatch(/^(TLS_AES_256_GCM_SHA384|TLS_CHACHA20_POLY1305_SHA256)$/);
      }
    });
  });
});
```

### Authentication Security

```typescript
// tests/security/network/authentication.test.ts
describe('Authentication Security Tests', () => {
  describe('Bearer Token Validation', () => {
    test('should reject requests without token', async () => {
      const response = await request(server)
        .post('/rpc')
        .send({ method: 'tools/list' })
        .expect(401);

      expect(response.body.error).toContain('Unauthorized');
    });

    test('should reject invalid bearer tokens', async () => {
      const response = await request(server)
        .post('/rpc')
        .set('Authorization', 'Bearer invalid-token')
        .send({ method: 'tools/list' })
        .expect(401);

      expect(response.body.error).toContain('Unauthorized');
    });

    test('should accept valid bearer tokens', async () => {
      const validToken = process.env.MCP_AUTH_TOKEN || 'test-token';
      
      const response = await request(server)
        .post('/rpc')
        .set('Authorization', `Bearer ${validToken}`)
        .send({ method: 'tools/list' })
        .expect(200);

      expect(response.body.result).toBeDefined();
    });

    test('should handle token timing attacks', async () => {
      const start = Date.now();
      await request(server)
        .post('/rpc')
        .set('Authorization', 'Bearer wrong-token-1')
        .send({ method: 'tools/list' });
      const time1 = Date.now() - start;

      const start2 = Date.now();
      await request(server)
        .post('/rpc')
        .set('Authorization', 'Bearer wrong-token-2-much-longer')
        .send({ method: 'tools/list' });
      const time2 = Date.now() - start2;

      // Response times should be similar to prevent timing attacks
      expect(Math.abs(time1 - time2)).toBeLessThan(10);
    });
  });
});
```

---

## 📦 Container Security Tests

### User Privileges Validation

```typescript
// tests/security/container/user-privileges.test.ts
import Docker from 'dockerode';

describe('Container User Privileges Tests', () => {
  let docker: Docker;
  let container: Docker.Container;

  beforeAll(() => {
    docker = new Docker();
  });

  describe('Non-root Execution', () => {
    test('should run as non-root user', async () => {
      const exec = await container.exec({
        Cmd: ['id', '-u'],
        AttachStdout: true,
      });

      const stream = await exec.start({ hijack: true, stdin: false });
      const output = await streamToString(stream);
      
      expect(output.trim()).not.toBe('0'); // Not root
      expect(output.trim()).toBe('1001');  // mcp-server user
    });

    test('should not have sudo capabilities', async () => {
      const exec = await container.exec({
        Cmd: ['sudo', 'ls'],
        AttachStdout: true,
        AttachStderr: true,
      });

      const stream = await exec.start({ hijack: true, stdin: false });
      const output = await streamToString(stream);
      
      expect(output).toContain('command not found');
    });

    test('should not be able to access sensitive files', async () => {
      const sensitiveFiles = ['/etc/passwd', '/etc/shadow', '/root'];
      
      for (const file of sensitiveFiles) {
        const exec = await container.exec({
          Cmd: ['cat', file],
          AttachStderr: true,
        });

        const stream = await exec.start({ hijack: true, stdin: false });
        const output = await streamToString(stream);
        
        expect(output).toContain('Permission denied');
      }
    });
  });
});
```

### Filesystem Security

```typescript
// tests/security/container/filesystem.test.ts
describe('Container Filesystem Security Tests', () => {
  describe('Read-only Root Filesystem', () => {
    test('should have read-only root filesystem in production', async () => {
      const exec = await container.exec({
        Cmd: ['touch', '/test-write'],
        AttachStderr: true,
      });

      const stream = await exec.start({ hijack: true, stdin: false });
      const output = await streamToString(stream);
      
      expect(output).toContain('Read-only file system');
    });

    test('should allow writes to designated directories', async () => {
      const writableDirs = ['/tmp', '/workspace'];
      
      for (const dir of writableDirs) {
        const exec = await container.exec({
          Cmd: ['touch', `${dir}/test-file`],
          AttachStdout: true,
        });

        const stream = await exec.start({ hijack: true, stdin: false });
        await exec.inspect(); // Wait for completion
        
        const checkExec = await container.exec({
          Cmd: ['ls', `${dir}/test-file`],
          AttachStdout: true,
        });

        const checkStream = await checkExec.start({ hijack: true, stdin: false });
        const output = await streamToString(checkStream);
        
        expect(output.trim()).toBe(`${dir}/test-file`);
      }
    });
  });

  describe('Volume Security', () => {
    test('should have proper SELinux contexts', async () => {
      if (process.platform === 'linux') {
        const exec = await container.exec({
          Cmd: ['ls', '-Z', '/workspace'],
          AttachStdout: true,
        });

        const stream = await exec.start({ hijack: true, stdin: false });
        const output = await streamToString(stream);
        
        expect(output).toContain('container_file_t');
      }
    });
  });
});
```

---

## ☸️ Kubernetes Security Tests

### Pod Security Standards

```typescript
// tests/security/kubernetes/pod-security.test.ts
import { KubeConfig, CoreV1Api } from '@kubernetes/client-node';

describe('Kubernetes Pod Security Tests', () => {
  let k8sApi: CoreV1Api;

  beforeAll(() => {
    const kc = new KubeConfig();
    kc.loadFromDefault();
    k8sApi = kc.makeApiClient(CoreV1Api);
  });

  describe('Security Context Validation', () => {
    test('should enforce non-root security context', async () => {
      const pods = await k8sApi.listNamespacedPod('default', undefined, undefined, undefined, undefined, 'app=huskycats-mcp');
      
      for (const pod of pods.body.items) {
        expect(pod.spec?.securityContext?.runAsNonRoot).toBe(true);
        expect(pod.spec?.securityContext?.runAsUser).toBeGreaterThan(0);
        
        for (const container of pod.spec?.containers || []) {
          expect(container.securityContext?.allowPrivilegeEscalation).toBe(false);
          expect(container.securityContext?.readOnlyRootFilesystem).toBe(true);
          expect(container.securityContext?.capabilities?.drop).toContain('ALL');
        }
      }
    });

    test('should have resource limits enforced', async () => {
      const pods = await k8sApi.listNamespacedPod('default', undefined, undefined, undefined, undefined, 'app=huskycats-mcp');
      
      for (const pod of pods.body.items) {
        for (const container of pod.spec?.containers || []) {
          expect(container.resources?.limits?.cpu).toBeDefined();
          expect(container.resources?.limits?.memory).toBeDefined();
          expect(container.resources?.requests?.cpu).toBeDefined();
          expect(container.resources?.requests?.memory).toBeDefined();
        }
      }
    });
  });

  describe('Network Policies', () => {
    test('should have network policies defined', async () => {
      const networkPolicies = await k8sApi.listNamespacedNetworkPolicy('default');
      const mcpPolicies = networkPolicies.body.items.filter(
        policy => policy.spec?.podSelector?.matchLabels?.app === 'huskycats-mcp'
      );
      
      expect(mcpPolicies.length).toBeGreaterThan(0);
    });
  });
});
```

### Horizontal Pod Autoscaler Security

```typescript
// tests/security/kubernetes/hpa-security.test.ts
describe('HPA Security Tests', () => {
  describe('Scaling Limits', () => {
    test('should have reasonable scaling limits', async () => {
      const hpa = await k8sApi.listNamespacedHorizontalPodAutoscaler('default', undefined, undefined, undefined, undefined, 'app=huskycats-mcp');
      
      for (const autoscaler of hpa.body.items) {
        expect(autoscaler.spec?.minReplicas).toBeGreaterThanOrEqual(1);
        expect(autoscaler.spec?.maxReplicas).toBeLessThanOrEqual(20);
        
        // Should not scale too aggressively
        expect(autoscaler.spec?.targetCPUUtilizationPercentage).toBeGreaterThanOrEqual(50);
      }
    });

    test('should have proper metrics configuration', async () => {
      const hpa = await k8sApi.listNamespacedHorizontalPodAutoscaler('default');
      const mcpHPA = hpa.body.items.find(
        h => h.spec?.scaleTargetRef?.name === 'huskycats-mcp-server'
      );
      
      expect(mcpHPA).toBeDefined();
      expect(mcpHPA?.spec?.metrics).toBeDefined();
    });
  });
});
```

---

## 🔄 Syncthing Security Tests

### Configuration Validation

```typescript
// tests/security/syncthing/config-validation.test.ts
describe('Syncthing Security Tests', () => {
  describe('Configuration Security', () => {
    test('should have secure API key configuration', async () => {
      const config = await fs.readFile('/mnt/syncthing/config.xml', 'utf8');
      const parser = new DOMParser();
      const doc = parser.parseFromString(config, 'text/xml');
      
      const apiKey = doc.querySelector('configuration > gui > apikey')?.textContent;
      expect(apiKey).toBeDefined();
      expect(apiKey?.length).toBeGreaterThanOrEqual(32);
    });

    test('should restrict GUI access', async () => {
      const config = await fs.readFile('/mnt/syncthing/config.xml', 'utf8');
      const parser = new DOMParser();
      const doc = parser.parseFromString(config, 'text/xml');
      
      const address = doc.querySelector('configuration > gui > address')?.textContent;
      expect(address).toBe('127.0.0.1:8384'); // Only localhost
    });

    test('should have folders configured as receive-only', async () => {
      const response = await fetch('http://localhost:8384/rest/config/folders', {
        headers: {
          'X-API-Key': process.env.SYNCTHING_API_KEY || 'test-key'
        }
      });
      
      const folders = await response.json();
      
      for (const folder of folders) {
        expect(folder.type).toBe('receiveonly');
        expect(folder.rescanIntervalS).toBeLessThanOrEqual(3600);
      }
    });
  });

  describe('Access Control', () => {
    test('should prevent unauthorized device connections', async () => {
      const response = await fetch('http://localhost:8384/rest/config/devices', {
        headers: {
          'X-API-Key': process.env.SYNCTHING_API_KEY || 'test-key'
        }
      });
      
      const devices = await response.json();
      
      // Should have a limited number of trusted devices
      expect(devices.length).toBeLessThanOrEqual(10);
      
      for (const device of devices) {
        expect(device.deviceID).toMatch(/^[A-Z0-9]{7}-[A-Z0-9]{7}-[A-Z0-9]{7}-[A-Z0-9]{7}-[A-Z0-9]{7}-[A-Z0-9]{7}-[A-Z0-9]{7}-[A-Z0-9]{7}$/);
      }
    });
  });
});
```

---

## 🐳 Podman Desktop Integration Tests

### Container Management Security

```typescript
// tests/integration/podman-desktop.test.ts
describe('Podman Desktop Integration Security Tests', () => {
  describe('Container Lifecycle', () => {
    test('should create containers with secure defaults', async () => {
      const containerInfo = await podman.getContainer('huskycats-mcp-server').inspect();
      
      // Security options
      expect(containerInfo.HostConfig.SecurityOpt).toContain('no-new-privileges:true');
      expect(containerInfo.Config.User).toBe('1001:1001');
      
      // Network security
      expect(containerInfo.HostConfig.NetworkMode).not.toBe('host');
      expect(containerInfo.HostConfig.Privileged).toBe(false);
      
      // Capability restrictions
      expect(containerInfo.HostConfig.CapDrop).toContain('ALL');
    });

    test('should mount volumes with proper security contexts', async () => {
      const containerInfo = await podman.getContainer('huskycats-mcp-server').inspect();
      
      for (const mount of containerInfo.Mounts) {
        if (mount.Type === 'bind') {
          expect(mount.Options).toContain('z'); // SELinux context
        }
      }
    });
  });

  describe('Image Security', () => {
    test('should use signed and verified images', async () => {
      const imageInfo = await podman.getImage('huskycats-mcp-server:latest').inspect();
      
      // Check for security labels
      expect(imageInfo.Config.Labels).toBeDefined();
      expect(imageInfo.Config.User).toBe('1001');
      expect(imageInfo.RootFS.Type).toBe('layers');
    });
  });
});
```

---

## 📊 Test Execution and Reporting

### Test Runner Configuration

```json
// jest.config.js
{
  "testEnvironment": "node",
  "setupFilesAfterEnv": ["<rootDir>/tests/setup.ts"],
  "testMatch": [
    "**/tests/security/**/*.test.ts",
    "**/tests/integration/**/*.test.ts"
  ],
  "collectCoverageFrom": [
    "src/**/*.ts",
    "!src/**/*.d.ts"
  ],
  "coverageThreshold": {
    "global": {
      "branches": 80,
      "functions": 80,
      "lines": 80,
      "statements": 80
    }
  },
  "reporters": [
    "default",
    ["jest-junit", {
      "outputDirectory": "test-results",
      "outputName": "security-tests.xml"
    }],
    ["jest-html-reporter", {
      "pageTitle": "HuskyCats MCP Server Security Test Report",
      "outputPath": "test-results/security-report.html"
    }]
  ]
}
```

### Security Test Execution

```bash
# Run all security tests
npm run test:security

# Run specific security domain tests
npm run test:security:infrastructure
npm run test:security:network
npm run test:security:container
npm run test:security:kubernetes
npm run test:security:syncthing

# Run integration tests
npm run test:integration

# Generate security report
npm run test:security:report
```

### Continuous Security Testing

```yaml
# .github/workflows/security-tests.yml
name: Security Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  security-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        
    - name: Install dependencies
      run: npm ci
      
    - name: Run security tests
      run: npm run test:security
      env:
        MCP_AUTH_TOKEN: ${{ secrets.TEST_MCP_AUTH_TOKEN }}
        
    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: security-test-results
        path: test-results/
```

---

## 🎯 Security Test Checklist

### Infrastructure Security ✅
- [ ] fail2ban configuration validation
- [ ] firewalld rules verification  
- [ ] SSH hardening enforcement
- [ ] System service security validation
- [ ] Log monitoring and alerting

### Network Security ✅
- [ ] RPC/HTTP transport security
- [ ] Bearer token authentication
- [ ] CORS policy enforcement
- [ ] Rate limiting validation
- [ ] TLS configuration verification

### Container Security ✅
- [ ] Non-root execution validation
- [ ] Filesystem permissions testing
- [ ] Resource limits enforcement
- [ ] Security context validation
- [ ] Image vulnerability scanning

### Kubernetes Security ✅
- [ ] Pod security standards compliance
- [ ] RBAC configuration validation
- [ ] Network policies testing
- [ ] HPA security validation
- [ ] Secrets management verification

### Syncthing Security ✅
- [ ] Configuration validation
- [ ] Access control mechanisms
- [ ] Data integrity verification
- [ ] Device authentication testing
- [ ] API security validation

### Integration Security ✅
- [ ] Podman Desktop security integration
- [ ] End-to-end security validation
- [ ] Multi-container security testing
- [ ] Service mesh security (if applicable)
- [ ] External service integration security

---

## 🚨 Security Incident Response

### Automated Response
- Immediate container isolation
- Network policy enforcement
- Alert generation and notification
- Log collection and preservation
- Forensic data capture

### Manual Response Procedures
1. **Incident Assessment**
   - Determine scope and impact
   - Identify affected systems
   - Assess data exposure risk

2. **Containment**
   - Isolate affected containers
   - Block malicious network traffic
   - Preserve evidence

3. **Eradication**
   - Remove malicious components
   - Patch vulnerabilities
   - Update security configurations

4. **Recovery**
   - Restore services from clean backups
   - Implement additional monitoring
   - Verify system integrity

5. **Lessons Learned**
   - Document incident details
   - Update security procedures
   - Enhance testing coverage

---

## 📈 Security Metrics and Monitoring

### Key Security Metrics
- Authentication failure rate
- Network intrusion attempts
- Container privilege escalations
- Resource usage anomalies
- Configuration drift detection

### Monitoring Implementation
```typescript
// Security metrics collection
export const securityMetrics = {
  authFailures: new prometheus.Counter({
    name: 'mcp_auth_failures_total',
    help: 'Total number of authentication failures',
    labelNames: ['source_ip', 'user_agent']
  }),
  
  privilegeEscalations: new prometheus.Counter({
    name: 'mcp_privilege_escalations_total',
    help: 'Total number of privilege escalation attempts'
  }),
  
  networkConnections: new prometheus.Gauge({
    name: 'mcp_network_connections_active',
    help: 'Number of active network connections'
  })
};
```

This comprehensive security testing framework ensures that the HuskyCats MCP Server maintains robust security across all deployment scenarios while providing clear validation of security controls and rapid incident response capabilities.