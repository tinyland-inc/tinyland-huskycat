#!/usr/bin/env python3
"""
GitLab CI Schema Validation Script
Uses the official GitLab CI JSON Schema for comprehensive validation
"""

import sys
import os
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gitlab_ci_validator import GitLabCISchemaValidator


def main():
    """Main validation entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Validate GitLab CI YAML files against official schema'
    )
    parser.add_argument('file', nargs='?', default='.gitlab-ci.yml',
                       help='Path to .gitlab-ci.yml file (default: .gitlab-ci.yml)')
    parser.add_argument('--refresh', action='store_true', 
                       help='Force refresh of cached schema')
    parser.add_argument('--info', action='store_true',
                       help='Show schema information')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(levelname)s: %(message)s'
    )
    
    # Create validator with schema caching
    print(f"INFO: Validating GitLab CI file: {args.file}")
    
    try:
        validator = GitLabCISchemaValidator(force_refresh=args.refresh)
        
        if args.info:
            info = validator.get_schema_info()
            print("\nGitLab CI Schema Information:")
            for key, value in info.items():
                print(f"  {key}: {value}")
            return 0
        
        # Check if using cached schema
        if validator.SCHEMA_CACHE_FILE.exists() and not args.refresh:
            print("INFO: Using cached GitLab CI schema")
        else:
            print("INFO: Fetched fresh GitLab CI schema")
        
        # Validate file
        is_valid, errors, warnings = validator.validate_file(args.file)
        
        # Output results
        if errors:
            print("\n❌ VALIDATION FAILED")
            print("Errors found:")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
        
        if warnings:
            print("\n⚠️  WARNINGS")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")
        
        if is_valid:
            print("\n✅ VALIDATION PASSED" + (" (with warnings)" if warnings else ""))
        
        print(f"\nSummary: {len(errors)} errors, {len(warnings)} warnings")
        
        # Exit code
        return 0 if is_valid else 1
        
    except Exception as e:
        print(f"ERROR: Validation failed with exception: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())