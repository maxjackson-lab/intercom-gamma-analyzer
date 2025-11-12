#!/usr/bin/env python3
"""
Import/Dependency Checker

Validates that all imports are available:
1. All imports exist in requirements.txt (or are stdlib)
2. Deployment requirements match dev requirements
3. No missing dependencies

Prevents: ModuleNotFoundError in deployment
Priority: P0 (Critical)
"""

import ast
import sys
from pathlib import Path
from typing import Set, List, Dict, Any


# Python standard library modules (Python 3.11)
STDLIB_MODULES = {
    'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio', 'asyncore',
    'atexit', 'audioop', 'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'builtins',
    'bz2', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs',
    'codeop', 'collections', 'colorsys', 'compileall', 'concurrent', 'configparser',
    'contextlib', 'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt', 'csv',
    'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib',
    'dis', 'distutils', 'doctest', 'email', 'encodings', 'enum', 'errno', 'faulthandler',
    'fcntl', 'filecmp', 'fileinput', 'fnmatch', 'formatter', 'fractions', 'ftplib',
    'functools', 'gc', 'getopt', 'getpass', 'gettext', 'glob', 'graphlib', 'grp',
    'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http', 'imaplib', 'imghdr', 'imp',
    'importlib', 'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword',
    'lib2to3', 'linecache', 'locale', 'logging', 'lzma', 'mailbox', 'mailcap',
    'marshal', 'math', 'mimetypes', 'mmap', 'modulefinder', 'multiprocessing',
    'netrc', 'nis', 'nntplib', 'numbers', 'operator', 'optparse', 'os', 'ossaudiodev',
    'parser', 'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil', 'platform',
    'plistlib', 'poplib', 'posix', 'posixpath', 'pprint', 'profile', 'pstats', 'pty',
    'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue', 'quopri', 'random', 're',
    'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy', 'sched', 'secrets',
    'select', 'selectors', 'shelve', 'shlex', 'shutil', 'signal', 'site', 'smtpd',
    'smtplib', 'sndhdr', 'socket', 'socketserver', 'spwd', 'sqlite3', 'ssl', 'stat',
    'statistics', 'string', 'stringprep', 'struct', 'subprocess', 'sunau', 'symbol',
    'symtable', 'sys', 'sysconfig', 'syslog', 'tabnanny', 'tarfile', 'telnetlib',
    'tempfile', 'termios', 'test', 'textwrap', 'threading', 'time', 'timeit', 'tkinter',
    'token', 'tokenize', 'tomllib', 'trace', 'traceback', 'tracemalloc', 'tty', 'turtle',
    'turtledemo', 'types', 'typing', 'typing_extensions', 'unicodedata', 'unittest',
    'urllib', 'uu', 'uuid', 'venv', 'warnings', 'wave', 'weakref', 'webbrowser',
    'winreg', 'winsound', 'wsgiref', 'xdrlib', 'xml', 'xmlrpc', 'zipapp', 'zipfile',
    'zipimport', 'zlib', '__future__', '__main__', '_thread'
}


class ImportChecker:
    """Check imports against requirements."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / 'src'
        self.requirements_file = project_root / 'requirements.txt'
        self.railway_requirements = project_root / 'requirements-railway.txt'
        self.errors: List[Dict[str, Any]] = []
    
    def check_all(self) -> List[Dict[str, Any]]:
        """Run all import checks."""
        # Extract all imports from source code
        all_imports = self._extract_all_imports()
        
        # Load requirements
        dev_requirements = self._load_requirements(self.requirements_file)
        railway_requirements = self._load_requirements(self.railway_requirements) if self.railway_requirements.exists() else set()
        
        # Check imports against requirements
        self._check_imports_in_requirements(all_imports, dev_requirements)
        
        # Check Railway sync
        if railway_requirements:
            self._check_railway_sync(dev_requirements, railway_requirements)
        
        return self.errors
    
    def _extract_all_imports(self) -> Set[str]:
        """Extract all import statements from source code."""
        all_imports = set()
        
        for py_file in self.src_dir.rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue
            
            try:
                content = py_file.read_text()
                tree = ast.parse(content, filename=str(py_file))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module = alias.name.split('.')[0]
                            all_imports.add(module)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module = node.module.split('.')[0]
                            all_imports.add(module)
            except:
                pass
        
        return all_imports
    
    def _load_requirements(self, req_file: Path) -> Set[str]:
        """Load package names from requirements file."""
        if not req_file.exists():
            return set()
        
        packages = set()
        for line in req_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Extract package name (before ==, >=, [, etc.)
            package = line.split('==')[0].split('>=')[0].split('[')[0].strip()
            # Normalize: some packages use - instead of _
            packages.add(package.lower())
            packages.add(package.replace('-', '_').lower())
            packages.add(package.replace('_', '-').lower())
        
        return packages
    
    def _check_imports_in_requirements(self, imports: Set[str], requirements: Set[str]):
        """Check if all imports are in requirements."""
        # Skip local modules and stdlib
        skip_modules = STDLIB_MODULES | {'src', 'tests', 'config', 'scripts'}
        
        for module in imports:
            if module in skip_modules:
                continue
            
            # Check if module is in requirements (with fuzzy matching)
            module_lower = module.lower()
            module_dash = module.replace('_', '-').lower()
            module_underscore = module.replace('-', '_').lower()
            
            if not any(req in requirements for req in [module_lower, module_dash, module_underscore]):
                self.errors.append({
                    'module': module,
                    'error': f'Import "{module}" not found in requirements.txt',
                    'severity': 'warning',
                    'fix': f'Add to requirements.txt or verify it\'s a stdlib module'
                })
    
    def _check_railway_sync(self, dev_reqs: Set[str], railway_reqs: Set[str]):
        """Check Railway requirements are in sync with dev requirements."""
        # Skip test-only packages
        test_packages = {'pytest', 'pytest-asyncio', 'pytest-cov', 'hypothesis', 'pytest-mock'}
        
        # Find packages in dev but not railway (excluding test packages)
        missing_in_railway = []
        for pkg in dev_reqs:
            if pkg in test_packages:
                continue
            if pkg not in railway_reqs:
                missing_in_railway.append(pkg)
        
        if missing_in_railway:
            self.errors.append({
                'error': 'Packages in requirements.txt missing from requirements-railway.txt',
                'packages': sorted(missing_in_railway),
                'severity': 'critical',
                'fix': 'Add these packages to requirements-railway.txt'
            })


def main():
    """Run import validation."""
    print("="*80)
    print("IMPORT/DEPENDENCY VALIDATION")
    print("="*80)
    print()
    
    project_root = Path(__file__).parent.parent
    checker = ImportChecker(project_root)
    
    errors = checker.check_all()
    
    if not errors:
        print("✅ No import/dependency issues found!")
        return 0
    
    # Group by severity
    critical = [e for e in errors if e.get('severity') == 'critical']
    warnings = [e for e in errors if e.get('severity') == 'warning']
    
    print(f"📊 Found {len(errors)} issue(s):")
    print(f"   Critical: {len(critical)}")
    print(f"   Warnings: {len(warnings)}")
    print()
    
    if critical:
        print("🔴 CRITICAL ISSUES:")
        for error in critical:
            print(f"   Error: {error['error']}")
            if 'packages' in error:
                for pkg in error['packages'][:10]:  # Show first 10
                    print(f"      - {pkg}")
                if len(error['packages']) > 10:
                    print(f"      ... and {len(error['packages']) - 10} more")
            print(f"   Fix: {error['fix']}")
            print()
    
    if warnings:
        print("⚠️  WARNINGS:")
        for error in warnings:
            if 'module' in error:
                print(f"   Module: {error['module']}")
            print(f"   Error: {error['error']}")
            print(f"   Fix: {error['fix']}")
            print()
    
    if critical:
        print("❌ Critical issues found - fix before deploying!")
        return 1
    else:
        print("⚠️  Only warnings found - review but can proceed")
        return 0


if __name__ == '__main__':
    sys.exit(main())




