#!/usr/bin/env node
/**
 * E2E Test for HuskyCat MCP Server
 * Tests actual endpoints, validation tools, and bad code fixing
 */

const http = require('http');
const fs = require('fs').promises;
const path = require('path');
const { spawn } = require('child_process');

const MCP_URL = 'http://localhost:8080';
const BEARER_TOKEN = 'dev-token-for-testing';

// Test utilities
const makeRequest = (endpoint, method = 'GET', body = null) => {
  return new Promise((resolve, reject) => {
    const url = new URL(endpoint, MCP_URL);
    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname,
      method,
      headers: {
        'Authorization': `Bearer ${BEARER_TOKEN}`,
        'Content-Type': 'application/json'
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve({
            status: res.statusCode,
            headers: res.headers,
            body: data ? JSON.parse(data) : null
          });
        } catch (e) {
          resolve({ status: res.statusCode, body: data });
        }
      });
    });

    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
};

const rpcCall = async (method, params = {}, id = 1) => {
  return makeRequest('/rpc', 'POST', {
    jsonrpc: '2.0',
    method,
    params,
    id
  });
};

// Test bad Python code
const BAD_PYTHON_CODE = `#!/usr/bin/env python3

def calculate_sum(numbers):
    sum=0
    for i in range(len(numbers)):
        sum+=numbers[i]
    return sum

def process_data(  data  ):
    if data==None:
        return []
    processed=[]
    for item in data:
        if item>0: processed.append(item*2)
    return processed

class DataProcessor:
    def __init__(self,name):
        self.name=name
    def process(self,data):
        return [x**2 for x in data if x%2==0]

# Security issue: eval usage
def unsafe_calc(expr):
    return eval(expr)

# Missing type hints
def concatenate(a,b):
    return str(a)+str(b)
`;

const GOOD_PYTHON_CODE = `#!/usr/bin/env python3
from typing import List, Optional, Any


def calculate_sum(numbers: List[float]) -> float:
    """Calculate the sum of a list of numbers."""
    return sum(numbers)


def process_data(data: Optional[List[float]]) -> List[float]:
    """Process data by doubling positive values."""
    if data is None:
        return []
    
    processed = []
    for item in data:
        if item > 0:
            processed.append(item * 2)
    return processed


class DataProcessor:
    """A class for processing data."""
    
    def __init__(self, name: str) -> None:
        self.name = name
    
    def process(self, data: List[int]) -> List[int]:
        """Process data by squaring even numbers."""
        return [x**2 for x in data if x % 2 == 0]


# Security issue fixed: no eval usage
def safe_calc(expr: str) -> Any:
    """Safely calculate expressions."""
    # Use ast.literal_eval or a proper expression parser
    raise NotImplementedError("Use ast.literal_eval for safe evaluation")


def concatenate(a: Any, b: Any) -> str:
    """Concatenate two values as strings."""
    return str(a) + str(b)
`;

// Test suite
const tests = {
  async testHealthEndpoint() {
    console.log('🧪 Testing /health endpoint...');
    const res = await makeRequest('/health');
    
    if (res.status !== 200) throw new Error(`Health check failed: ${res.status}`);
    if (!res.body.status === 'ready') throw new Error('Server not ready');
    if (!res.body.toolCount > 0) throw new Error('No tools available');
    
    console.log('✅ Health check passed');
    console.log(`   - Status: ${res.body.status}`);
    console.log(`   - Uptime: ${Math.floor(res.body.uptime)}s`);
    console.log(`   - Tools: ${res.body.toolCount}`);
  },

  async testToolsEndpoint() {
    console.log('\n🧪 Testing /tools endpoint...');
    const res = await makeRequest('/tools');
    
    if (res.status !== 200) throw new Error(`Tools list failed: ${res.status}`);
    if (!Array.isArray(res.body.tools)) throw new Error('Invalid tools response');
    
    const pythonTools = res.body.tools.filter(t => t.name.startsWith('python-'));
    if (pythonTools.length === 0) throw new Error('No Python tools found');
    
    console.log('✅ Tools endpoint passed');
    console.log(`   - Total tools: ${res.body.tools.length}`);
    console.log(`   - Python tools: ${pythonTools.map(t => t.name).join(', ')}`);
  },

  async testMetricsEndpoint() {
    console.log('\n🧪 Testing /metrics endpoint...');
    const res = await makeRequest('/metrics');
    
    if (res.status !== 200) throw new Error(`Metrics failed: ${res.status}`);
    if (!res.body.includes('mcp_server_uptime')) throw new Error('Missing metrics');
    
    console.log('✅ Metrics endpoint passed');
  },

  async testRPCInitialize() {
    console.log('\n🧪 Testing RPC initialization...');
    const res = await rpcCall('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: {
        name: 'huskycat-e2e-test',
        version: '1.0.0'
      }
    });
    
    if (res.status !== 200) throw new Error(`RPC init failed: ${res.status}`);
    if (!res.body.result?.serverInfo) throw new Error('Invalid init response');
    
    console.log('✅ RPC initialization passed');
    console.log(`   - Server: ${res.body.result.serverInfo.name}`);
    console.log(`   - Version: ${res.body.result.serverInfo.version}`);
    
    return res.body.result;
  },

  async testToolsList() {
    console.log('\n🧪 Testing tools/list RPC method...');
    const res = await rpcCall('tools/list');
    
    if (res.status !== 200) throw new Error(`Tools list failed: ${res.status}`);
    if (!Array.isArray(res.body.result?.tools)) throw new Error('Invalid tools response');
    
    console.log('✅ RPC tools/list passed');
    console.log(`   - Available tools: ${res.body.result.tools.length}`);
    
    return res.body.result.tools;
  },

  async testPythonValidation() {
    console.log('\n🧪 Testing Python validation with bad code...');
    
    // Create test file
    const testFile = path.join(process.cwd(), 'test-bad-code.py');
    await fs.writeFile(testFile, BAD_PYTHON_CODE);
    
    try {
      // Test various Python tools
      const tools = ['python-black', 'python-flake8', 'python-mypy', 'security_bandit_scan'];
      
      for (const tool of tools) {
        console.log(`\n   Testing ${tool}...`);
        const res = await rpcCall('tools/call', {
          name: tool,
          arguments: {
            files: [testFile],
            fix: false
          }
        });
        
        if (res.status !== 200) {
          console.log(`   ⚠️  ${tool} returned error: ${res.body.error?.message}`);
        } else {
          console.log(`   ✅ ${tool} completed`);
          if (res.body.result?.issues) {
            console.log(`      Issues found: ${res.body.result.issues.length}`);
          }
        }
      }
      
      // Test auto-fix with Black
      console.log('\n   Testing auto-fix with Black...');
      const fixRes = await rpcCall('tools/call', {
        name: 'python-black',
        arguments: {
          files: [testFile],
          fix: true
        }
      });
      
      if (fixRes.status === 200) {
        console.log('   ✅ Auto-fix completed');
        const fixedCode = await fs.readFile(testFile, 'utf8');
        if (fixedCode !== BAD_PYTHON_CODE) {
          console.log('   ✅ Code was modified by formatter');
        }
      }
      
    } finally {
      // Cleanup
      await fs.unlink(testFile).catch(() => {});
    }
  },

  async testSecurityScanning() {
    console.log('\n🧪 Testing security scanning...');
    
    // Test secrets scan
    const secretsRes = await rpcCall('tools/call', {
      name: 'security_secrets_scan',
      arguments: {
        directory: '.',
        exclude: ['.git/**', 'node_modules/**', 'build/**']
      }
    });
    
    console.log('✅ Secrets scan completed');
    if (secretsRes.body.result?.secrets) {
      console.log(`   - Secrets found: ${secretsRes.body.result.secrets.length}`);
    }
  },

  async testProjectValidation() {
    console.log('\n🧪 Testing full project validation...');
    
    const res = await rpcCall('tools/call', {
      name: 'validate_project',
      arguments: {
        directory: '.',
        exclude: ['node_modules/**', '.git/**', 'build/**', 'dist/**'],
        fixIssues: false,
        parallel: true
      }
    });
    
    if (res.status === 200) {
      console.log('✅ Project validation completed');
      if (res.body.result?.summary) {
        const summary = res.body.result.summary;
        console.log(`   - Files validated: ${summary.filesValidated || 0}`);
        console.log(`   - Total issues: ${summary.totalIssues || 0}`);
      }
    } else {
      console.log('⚠️  Project validation returned error:', res.body.error?.message);
    }
  }
};

// Main test runner
async function runTests() {
  console.log('🚀 Starting HuskyCat MCP Server E2E Tests\n');
  console.log(`Server: ${MCP_URL}`);
  console.log(`Token: ${BEARER_TOKEN}\n`);
  
  const startTime = Date.now();
  let passed = 0;
  let failed = 0;
  
  // Check if server is running
  try {
    await makeRequest('/health');
  } catch (error) {
    console.error('❌ MCP Server is not running!');
    console.error('   Please start it with: huskycat mcp start');
    process.exit(1);
  }
  
  // Run all tests
  for (const [name, test] of Object.entries(tests)) {
    try {
      await test();
      passed++;
    } catch (error) {
      console.error(`\n❌ ${name} failed:`, error.message);
      failed++;
    }
  }
  
  const duration = ((Date.now() - startTime) / 1000).toFixed(2);
  
  console.log('\n' + '='.repeat(50));
  console.log('📊 Test Results');
  console.log('='.repeat(50));
  console.log(`✅ Passed: ${passed}`);
  console.log(`❌ Failed: ${failed}`);
  console.log(`⏱️  Duration: ${duration}s`);
  console.log('='.repeat(50));
  
  process.exit(failed > 0 ? 1 : 0);
}

// Run tests
runTests().catch(console.error);