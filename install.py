#!/usr/bin/env python3
"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Standalone installer script.
Run this from the repository root to install Codebase Cartographer.

Usage:
    python install.py                      # Install in current directory
    python install.py /path/to/project     # Install in specific directory
    python install.py --force              # Force reinstall
"""

import os
import sys
from pathlib import Path


def main():
    """Main installer entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Install Codebase Cartographer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Install in current directory
    python install.py

    # Install in specific directory
    python install.py /path/to/project

    # Force reinstall
    python install.py --force

Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
"""
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

    project_path = Path(args.project_root).resolve()

    print("=" * 70)
    print("Codebase Cartographer - Installation")
    print("Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>")
    print("=" * 70)
    print(f"\nProject: {project_path}")

    # Check if we're in the source directory
    src_dir = Path(__file__).parent / 'src' / 'cartographer'

    if not src_dir.exists():
        print(f"\nError: Source directory not found at {src_dir}")
        print("Please run this script from the repository root.")
        sys.exit(1)

    # Add source to path
    sys.path.insert(0, str(Path(__file__).parent / 'src'))

    try:
        from cartographer.bootstrap import PortableInstaller

        installer = PortableInstaller(
            project_root=project_path,
            source_dir=src_dir
        )

        success = installer.install(force=args.force)
        sys.exit(0 if success else 1)

    except ImportError as e:
        print(f"\nError importing module: {e}")
        print("Please ensure all source files are present.")
        sys.exit(1)


if __name__ == '__main__':
    main()
