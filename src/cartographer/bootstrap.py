"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Portable, self-contained installation system.
Installs all dependencies locally in .claude-map/ directory.
"""

import os
import sys
import subprocess
import shutil
import json
import venv
from pathlib import Path
from typing import Optional, List


class PortableInstaller:
    """
    Install Codebase Cartographer with all dependencies in .claude-map/

    Features:
    - No system packages required
    - Fully portable (copy .claude-map/ anywhere)
    - Easy uninstall (rm -rf .claude-map)
    - Version-locked dependencies

    Usage:
        installer = PortableInstaller('/path/to/project')
        installer.install()
    """

    VERSION = "3.0.0"

    CORE_DEPENDENCIES = [
        'click>=8.0.0',
        'watchdog>=2.1.0',
        'tiktoken>=0.5.0',
    ]

    OPTIONAL_DEPENDENCIES = [
        'tree-sitter>=0.21.0',
    ]

    def __init__(self, project_root: Path, source_dir: Optional[Path] = None):
        self.project_root = Path(project_root).resolve()
        self.claude_dir = self.project_root / '.claude-map'
        self.venv_dir = self.claude_dir / 'venv'
        self.bin_dir = self.claude_dir / 'bin'
        self.src_dir = self.claude_dir / 'src'
        self.cache_dir = self.claude_dir / 'cache'
        self.logs_dir = self.claude_dir / 'logs'

        # Source directory (where the cartographer source is)
        if source_dir:
            self.source_dir = Path(source_dir).resolve()
        else:
            # Assume we're running from the source
            self.source_dir = Path(__file__).parent

        # Python executable paths
        self.system_python = sys.executable
        if sys.platform == 'win32':
            self.venv_python = self.venv_dir / 'Scripts' / 'python.exe'
            self.venv_pip = self.venv_dir / 'Scripts' / 'pip.exe'
        else:
            self.venv_python = self.venv_dir / 'bin' / 'python'
            self.venv_pip = self.venv_dir / 'bin' / 'pip'

    def install(self, force: bool = False) -> bool:
        """
        Run complete installation.

        Args:
            force: If True, overwrite existing installation

        Returns:
            True if successful, False otherwise
        """
        print("=" * 70)
        print("Codebase Cartographer - Portable Installation")
        print("Copyright (c) 2025 Breach Craft - Mike Piekarski")
        print("=" * 70)
        print(f"\nProject: {self.project_root}")
        print(f"Installation: {self.claude_dir}")
        print()

        # Check for existing installation
        if self.claude_dir.exists() and not force:
            if (self.venv_python).exists():
                print("Installation already exists.")
                print("Use --force to reinstall.")
                return False

        try:
            # Step 1: Create directory structure
            self._create_directories()

            # Step 2: Create virtual environment
            self._create_virtualenv()

            # Step 3: Upgrade pip
            self._upgrade_pip()

            # Step 4: Install dependencies
            self._install_dependencies()

            # Step 5: Copy source code
            self._copy_source()

            # Step 6: Create launcher scripts
            self._create_launchers()

            # Step 7: Create configuration
            self._create_config()

            # Step 8: Verify installation
            if not self._verify_installation():
                print("\nInstallation verification failed!")
                return False

            # Step 9: Install Claude Code integration
            self._install_claude_integration()

            print("\n" + "=" * 70)
            print("Installation Complete!")
            print("=" * 70)
            print(f"\nInstallation directory: {self.claude_dir}")
            print(f"\nUsage:")
            print(f"  {self.bin_dir / 'claude-map'} init")
            print(f"  {self.bin_dir / 'claude-map'} query 'find UserProfile'")
            print(f"  {self.bin_dir / 'claude-map'} stats")

            return True

        except Exception as e:
            print(f"\nInstallation failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _create_directories(self):
        """Create directory structure."""
        print("Creating directory structure...")

        directories = [
            self.claude_dir,
            self.venv_dir,
            self.bin_dir,
            self.src_dir,
            self.cache_dir,
            self.logs_dir,
        ]

        for d in directories:
            d.mkdir(parents=True, exist_ok=True)

        print(f"  Created {len(directories)} directories")

    def _create_virtualenv(self):
        """Create virtual environment."""
        print("\nCreating virtual environment...")

        if self.venv_python.exists():
            print("  Virtual environment already exists")
            return

        try:
            # Use venv module (built into Python 3.3+)
            builder = venv.EnvBuilder(with_pip=True, clear=True)
            builder.create(self.venv_dir)
            print(f"  Created at {self.venv_dir}")
        except Exception as e:
            print(f"  Error creating venv: {e}")
            raise

    def _upgrade_pip(self):
        """Upgrade pip in virtual environment."""
        print("\nUpgrading pip...")

        self._run_pip(['install', '--upgrade', 'pip', 'setuptools', 'wheel'])
        print("  pip upgraded")

    def _install_dependencies(self):
        """Install all dependencies in virtual environment."""
        print("\nInstalling dependencies...")

        # Install core dependencies
        print("  Core dependencies:")
        for dep in self.CORE_DEPENDENCIES:
            try:
                self._run_pip(['install', dep])
                print(f"    + {dep}")
            except Exception as e:
                print(f"    ! Failed: {dep} - {e}")
                raise

        # Install optional dependencies (don't fail if these don't work)
        print("  Optional dependencies:")
        for dep in self.OPTIONAL_DEPENDENCIES:
            try:
                self._run_pip(['install', dep])
                print(f"    + {dep}")
            except Exception as e:
                print(f"    - Skipped: {dep} (will use fallback)")

    def _run_pip(self, args: List[str]):
        """Run pip in virtual environment."""
        cmd = [str(self.venv_python), '-m', 'pip'] + args + ['--quiet']

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.claude_dir)
        )

        if result.returncode != 0:
            raise Exception(f"pip failed: {result.stderr}")

    def _copy_source(self):
        """Copy source code to installation directory."""
        print("\nCopying source code...")

        target_dir = self.src_dir / 'cartographer'
        target_dir.mkdir(parents=True, exist_ok=True)

        # Source files to copy
        source_files = [
            '__init__.py',
            '__main__.py',
            'database.py',
            'mapper.py',
            'parsers.py',
            'integration.py',
            'watcher.py',
            'benchmark.py',
            'cli.py',
            'bootstrap.py',
            'claude_integration.py',
            'session_tracker.py',
        ]

        copied = 0
        for filename in source_files:
            src = self.source_dir / filename
            dst = target_dir / filename

            if src.exists():
                shutil.copy2(src, dst)
                copied += 1
            else:
                print(f"  Warning: {filename} not found")

        print(f"  Copied {copied} source files")

    def _create_launchers(self):
        """Create launcher scripts."""
        print("\nCreating launcher scripts...")

        if sys.platform == 'win32':
            self._create_windows_launchers()
        else:
            self._create_unix_launchers()

        print("  Launcher scripts created")

    def _create_unix_launchers(self):
        """Create Unix/Linux/Mac launcher scripts."""
        # Main launcher
        launcher = self.bin_dir / 'claude-map'
        launcher_content = f'''#!/bin/bash
# Codebase Cartographer - Token-optimized codebase mapping
# Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
CLAUDE_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$CLAUDE_DIR/venv/bin/python"
SRC_DIR="$CLAUDE_DIR/src"

export PYTHONPATH="$SRC_DIR:$PYTHONPATH"
exec "$VENV_PYTHON" -m cartographer.cli "$@"
'''
        launcher.write_text(launcher_content)
        launcher.chmod(0o755)

        # Python launcher (for direct Python access)
        python_launcher = self.bin_dir / 'python'
        python_content = f'''#!/bin/bash
# Python with Cartographer environment

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
CLAUDE_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$CLAUDE_DIR/venv/bin/python"
SRC_DIR="$CLAUDE_DIR/src"

export PYTHONPATH="$SRC_DIR:$PYTHONPATH"
exec "$VENV_PYTHON" "$@"
'''
        python_launcher.write_text(python_content)
        python_launcher.chmod(0o755)

    def _create_windows_launchers(self):
        """Create Windows launcher scripts."""
        # Main launcher (.bat)
        launcher = self.bin_dir / 'claude-map.bat'
        launcher_content = f'''@echo off
REM Codebase Cartographer - Token-optimized codebase mapping
REM Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>

set SCRIPT_DIR=%~dp0
set CLAUDE_DIR=%SCRIPT_DIR%..
set VENV_PYTHON=%CLAUDE_DIR%\\venv\\Scripts\\python.exe
set SRC_DIR=%CLAUDE_DIR%\\src

set PYTHONPATH=%SRC_DIR%;%PYTHONPATH%
"%VENV_PYTHON%" -m cartographer.cli %*
'''
        launcher.write_text(launcher_content)

        # Python launcher
        python_launcher = self.bin_dir / 'python.bat'
        python_content = f'''@echo off
REM Python with Cartographer environment

set SCRIPT_DIR=%~dp0
set CLAUDE_DIR=%SCRIPT_DIR%..
set VENV_PYTHON=%CLAUDE_DIR%\\venv\\Scripts\\python.exe
set SRC_DIR=%CLAUDE_DIR%\\src

set PYTHONPATH=%SRC_DIR%;%PYTHONPATH%
"%VENV_PYTHON%" %*
'''
        python_launcher.write_text(python_content)

    def _create_config(self):
        """Create configuration file."""
        print("\nCreating configuration...")

        config = {
            'version': self.VERSION,
            'installation': {
                'type': 'portable',
                'project_root': str(self.project_root),
                'claude_dir': str(self.claude_dir),
                'installed_at': __import__('datetime').datetime.now().isoformat(),
            },
            'settings': {
                'max_workers': os.cpu_count() or 4,
                'cache_enabled': True,
                'watch_enabled': True,
                'max_cache_size_mb': 128,
                'ignore_patterns': [
                    'node_modules',
                    '.git',
                    '__pycache__',
                    'venv',
                    '.venv',
                    'dist',
                    'build',
                    '.next',
                    'coverage',
                    '.pytest_cache',
                ],
            },
            'languages': {
                'enabled': [
                    'python',
                    'javascript',
                    'typescript',
                    'go',
                    'ruby',
                    'jinja2',
                    'ejs',
                    'handlebars',
                ],
            },
            'attribution': {
                'author': 'Mike Piekarski',
                'email': 'mp@breachcraft.io',
                'company': 'Breach Craft',
                'copyright': 'Copyright (c) 2025 Breach Craft',
            }
        }

        config_file = self.claude_dir / 'config.json'
        config_file.write_text(json.dumps(config, indent=2))

        print(f"  Configuration saved to {config_file}")

    def _verify_installation(self) -> bool:
        """Verify installation is working."""
        print("\nVerifying installation...")

        # Check venv python exists
        if not self.venv_python.exists():
            print("  Error: Virtual environment Python not found")
            return False

        # Check we can import the module
        cmd = [
            str(self.venv_python),
            '-c',
            'import sys; sys.path.insert(0, "src"); from cartographer import __version__; print(__version__)'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.claude_dir)
        )

        if result.returncode != 0:
            print(f"  Error importing module: {result.stderr}")
            return False

        version = result.stdout.strip()
        print(f"  Cartographer version: {version}")

        # Check click is installed
        cmd = [str(self.venv_python), '-c', 'import click; print(click.__version__)']
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print("  Error: click not installed")
            return False

        print(f"  click version: {result.stdout.strip()}")

        print("  Verification passed!")
        return True

    def _install_claude_integration(self):
        """Install Claude Code integration (hooks, skills, commands)."""
        print("\nInstalling Claude Code integration...")

        try:
            from .claude_integration import ClaudeIntegrationInstaller
            installer = ClaudeIntegrationInstaller(
                self.project_root,
                source_dir=self.source_dir.parent / 'claude' if hasattr(self, 'source_dir') else None
            )
            installer.install()
        except ImportError:
            # Fallback: create minimal integration inline
            self._create_minimal_claude_integration()

    def _create_minimal_claude_integration(self):
        """Create minimal Claude integration without the full module."""
        claude_dir = self.project_root / '.claude'
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Use absolute paths to ensure hooks work from any working directory
        base_dir = str(self.project_root)
        claude_map_dir = str(self.claude_dir)

        # Create hooks directory
        hooks_dir = claude_dir / 'hooks'
        hooks_dir.mkdir(exist_ok=True)

        # Create update hook with absolute paths
        hook_content = f'''#!/bin/bash
# Codebase Cartographer auto-update hook

BASE_DIR="{base_dir}"
CLAUDE_MAP_DIR="{claude_map_dir}"

INPUT=$(cat)
TOOL=$(echo "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\\([^"]*\\)"$/\\1/')
case "$TOOL" in Edit|Write|NotebookEdit)
    FILE=$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\\([^"]*\\)"$/\\1/')
    if [ -n "$FILE" ] && [ -f "${{CLAUDE_MAP_DIR}}/codebase.db" ]; then
        mkdir -p "${{CLAUDE_MAP_DIR}}/cache"
        echo "$FILE" >> "${{CLAUDE_MAP_DIR}}/cache/update_queue.txt" 2>/dev/null
    fi
    ;;
esac
exit 0
'''
        hook_path = hooks_dir / 'cartographer-update.sh'
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)

        # Create skills directory
        skills_dir = claude_dir / 'skills'
        skills_dir.mkdir(exist_ok=True)

        # Create skill file
        skill_content = '''# Codebase Cartographer

Use `.claude-map/bin/claude-map` for token-efficient code exploration:

```bash
.claude-map/bin/claude-map find <name>    # Find component
.claude-map/bin/claude-map query "<text>" # Natural language query
.claude-map/bin/claude-map show <file>    # Show file components
.claude-map/bin/claude-map update         # Update map
```

**Best Practice**: Search before reading files to save 95%+ tokens.
'''
        (skills_dir / 'cartographer.md').write_text(skill_content)

        # Absolute paths for settings.json hook commands
        update_hook_cmd = str(hooks_dir / 'cartographer-update.sh')
        finalize_hook_cmd = str(hooks_dir / 'cartographer-finalize.sh')

        # Update settings.json (matcher is pipe-separated string)
        settings_path = claude_dir / 'settings.json'
        settings = {}
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text())
            except:
                pass

        settings.setdefault('hooks', {})
        settings['hooks']['PostToolUse'] = settings['hooks'].get('PostToolUse', [])
        settings['hooks']['PostToolUse'].append({
            'matcher': 'Edit|Write|NotebookEdit',
            'hooks': [
                {
                    'type': 'command',
                    'command': update_hook_cmd
                }
            ]
        })

        # Create finalize hook with absolute paths
        finalize_content = f'''#!/bin/bash
# Codebase Cartographer - Session end hook
# Processes queued updates when session ends

BASE_DIR="{base_dir}"
CLAUDE_MAP_DIR="{claude_map_dir}"
CLAUDE_MAP="${{CLAUDE_MAP_DIR}}/bin/claude-map"

if [ -f "${{CLAUDE_MAP_DIR}}/codebase.db" ] && [ -f "${{CLAUDE_MAP_DIR}}/cache/update_queue.txt" ]; then
    "$CLAUDE_MAP" update 2>/dev/null || true
    rm -f "${{CLAUDE_MAP_DIR}}/cache/update_queue.txt" 2>/dev/null || true
fi
exit 0
'''
        finalize_path = hooks_dir / 'cartographer-finalize.sh'
        finalize_path.write_text(finalize_content)
        finalize_path.chmod(0o755)

        # Add Stop hook to settings
        settings['hooks']['Stop'] = settings['hooks'].get('Stop', [])
        settings['hooks']['Stop'].append({
            'matcher': '',
            'hooks': [
                {
                    'type': 'command',
                    'command': finalize_hook_cmd
                }
            ]
        })

        # Add permissions to whitelist cartographer commands
        claude_map_cmd = str(self.claude_dir / 'bin' / 'claude-map')
        cartographer_permissions = [
            f"Bash({claude_map_cmd}:*)",  # All claude-map subcommands
        ]

        # Initialize permissions if not present, preserve existing
        if 'permissions' not in settings:
            settings['permissions'] = {}
        if 'allow' not in settings['permissions']:
            settings['permissions']['allow'] = []

        # Append our permissions (avoid duplicates)
        existing_allows = settings['permissions']['allow']
        for perm in cartographer_permissions:
            if perm not in existing_allows:
                existing_allows.append(perm)

        settings['permissions']['allow'] = existing_allows

        settings_path.write_text(json.dumps(settings, indent=2))

        # Update CLAUDE.md with cartographer instructions
        self._update_claude_md()

        print("    + Created hooks, skills, permissions, and updated CLAUDE.md")

    def _update_claude_md(self):
        """Update or create project CLAUDE.md with cartographer instructions at top."""
        claude_md = self.project_root / 'CLAUDE.md'

        cartographer_section = '''
## CRITICAL: Use Codebase Cartographer First

**BEFORE using Read, Grep, or Glob tools to explore code, you MUST use the cartographer:**

```bash
.claude-map/bin/claude-map find <name>      # Find function/class/component by name
.claude-map/bin/claude-map query "<text>"   # Natural language search
.claude-map/bin/claude-map show <file>      # Show file structure without reading full content
```

**Why this matters:**
- Saves 95%+ tokens compared to reading full files
- Returns precise line numbers and signatures
- Use Read tool ONLY after cartographer identifies the specific lines you need

**Workflow:**
1. `claude-map find ComponentName` → get file path and line numbers
2. `Read` tool with specific line range if you need implementation details

**Fallback:** If cartographer returns no results, you may use native Grep/Glob/Read tools.
'''

        if claude_md.exists():
            content = claude_md.read_text()
            if 'Codebase Cartographer' not in content:
                # Insert after the first header line, not at the end
                lines = content.split('\n')
                insert_idx = 0

                # Find the end of the first header block (# Title + optional blank line)
                for i, line in enumerate(lines):
                    if line.startswith('# '):
                        insert_idx = i + 1
                        # Skip any blank lines after the header
                        while insert_idx < len(lines) and lines[insert_idx].strip() == '':
                            insert_idx += 1
                        break

                # Insert the cartographer section
                lines.insert(insert_idx, cartographer_section)
                claude_md.write_text('\n'.join(lines))
                print("    + Updated CLAUDE.md (inserted at top)")
            else:
                print("    = CLAUDE.md already has cartographer section")
        else:
            # Create new CLAUDE.md
            claude_md.write_text(f"# Project Instructions\n{cartographer_section}")
            print("    + Created CLAUDE.md with cartographer instructions")


def install_portable(project_root: str = None, force: bool = False) -> bool:
    """
    Main entry point for portable installation.

    Usage:
        python -m cartographer.bootstrap /path/to/project
    """
    if project_root is None:
        project_root = os.getcwd()

    installer = PortableInstaller(Path(project_root))
    return installer.install(force=force)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Install Codebase Cartographer (portable, self-contained)'
    )
    parser.add_argument(
        'project_root',
        nargs='?',
        default=os.getcwd(),
        help='Project root directory (default: current directory)'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force reinstall even if already installed'
    )

    args = parser.parse_args()

    success = install_portable(args.project_root, force=args.force)
    sys.exit(0 if success else 1)
