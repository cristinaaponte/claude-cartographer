"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Main codebase mapping orchestration.
Handles file discovery, parallel processing, and incremental updates.
"""

import os
import sys
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
import threading

from .database import TokenOptimizedDatabase, ComponentData
from .parsers import (
    LanguageDetector,
    ParseResult,
    get_parser_for_file,
    get_supported_languages,
)


@dataclass
class PerformanceMetrics:
    """Track performance metrics during mapping."""
    start_time: float = 0.0
    end_time: float = 0.0
    files_processed: int = 0
    files_skipped: int = 0
    components_found: int = 0
    relationships_found: int = 0
    errors: int = 0
    bytes_processed: int = 0

    def duration(self) -> float:
        """Get duration in seconds."""
        return self.end_time - self.start_time

    def files_per_second(self) -> float:
        """Get processing rate."""
        duration = self.duration()
        if duration > 0:
            return self.files_processed / duration
        return 0.0


class PerformanceMonitor:
    """Monitor and report performance metrics."""

    def __init__(self):
        self.metrics = PerformanceMetrics()
        self._lock = threading.Lock()

    def start(self):
        """Start timing."""
        self.metrics.start_time = time.time()

    def stop(self):
        """Stop timing."""
        self.metrics.end_time = time.time()

    def record_file(self, success: bool = True, size: int = 0):
        """Record a processed file."""
        with self._lock:
            if success:
                self.metrics.files_processed += 1
                self.metrics.bytes_processed += size
            else:
                self.metrics.errors += 1

    def record_skip(self):
        """Record a skipped file."""
        with self._lock:
            self.metrics.files_skipped += 1

    def record_components(self, count: int):
        """Record found components."""
        with self._lock:
            self.metrics.components_found += count

    def record_relationships(self, count: int):
        """Record found relationships."""
        with self._lock:
            self.metrics.relationships_found += count

    def get_report(self) -> Dict[str, Any]:
        """Get performance report."""
        return {
            'duration_seconds': round(self.metrics.duration(), 2),
            'files_processed': self.metrics.files_processed,
            'files_skipped': self.metrics.files_skipped,
            'components_found': self.metrics.components_found,
            'relationships_found': self.metrics.relationships_found,
            'errors': self.metrics.errors,
            'files_per_second': round(self.metrics.files_per_second(), 1),
            'bytes_processed': self.metrics.bytes_processed,
            'mb_processed': round(self.metrics.bytes_processed / 1024 / 1024, 2),
        }


class HashCache:
    """Cache file hashes for incremental updates."""

    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.hashes: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        """Load hash cache from disk."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r') as f:
                    self.hashes = json.load(f)
            except:
                self.hashes = {}

    def save(self):
        """Save hash cache to disk."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, 'w') as f:
            json.dump(self.hashes, f)

    def get_hash(self, file_path: str) -> Optional[str]:
        """Get cached hash for a file."""
        entry = self.hashes.get(file_path)
        return entry.get('hash') if entry else None

    def set_hash(self, file_path: str, file_hash: str, mtime: float, size: int):
        """Set hash for a file."""
        self.hashes[file_path] = {
            'hash': file_hash,
            'mtime': mtime,
            'size': size,
        }

    def needs_update(self, file_path: str, mtime: float, size: int) -> bool:
        """Check if file needs re-processing (quick check using mtime+size)."""
        entry = self.hashes.get(file_path)
        if not entry:
            return True

        # Quick check: mtime and size
        if entry.get('mtime') != mtime or entry.get('size') != size:
            return True

        return False

    def remove(self, file_path: str):
        """Remove a file from cache."""
        self.hashes.pop(file_path, None)

    def get_cached_files(self) -> Set[str]:
        """Get set of all cached file paths."""
        return set(self.hashes.keys())


class CodebaseMapper:
    """
    Main codebase mapping orchestrator.

    Usage:
        mapper = CodebaseMapper('/path/to/project')
        mapper.map_directory()  # Full mapping
        mapper.map_directory(incremental=True)  # Incremental update
        mapper.map_file('/path/to/file.py')  # Single file
    """

    DEFAULT_IGNORE_PATTERNS = [
        'node_modules',
        '.git',
        '__pycache__',
        'venv',
        '.venv',
        'env',
        '.env',
        'dist',
        'build',
        '.next',
        'coverage',
        '.pytest_cache',
        '.mypy_cache',
        '.tox',
        'eggs',
        '*.egg-info',
        '.claude-map',
        '.idea',
        '.vscode',
        'vendor',
        'target',
    ]

    def __init__(
        self,
        project_root: Path,
        max_workers: Optional[int] = None,
        use_multiprocessing: bool = True,
        ignore_patterns: Optional[List[str]] = None,
    ):
        self.project_root = Path(project_root).resolve()
        self.claude_dir = self.project_root / '.claude-map'
        self.db_path = self.claude_dir / 'codebase.db'
        self.cache_dir = self.claude_dir / 'cache'

        # Create directories
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.db = TokenOptimizedDatabase(self.db_path)
        self.hash_cache = HashCache(self.cache_dir / 'file_hashes.json')
        self.language_detector = LanguageDetector()
        self.monitor = PerformanceMonitor()

        # Configuration
        self.max_workers = max_workers or os.cpu_count() or 4
        self.use_multiprocessing = use_multiprocessing
        self.ignore_patterns = ignore_patterns or self.DEFAULT_IGNORE_PATTERNS

        # Progress tracking
        self._progress_callback = None
        self._total_files = 0
        self._processed_files = 0

    def set_progress_callback(self, callback):
        """Set a callback for progress updates: callback(current, total, message)"""
        self._progress_callback = callback

    def _report_progress(self, message: str = ""):
        """Report progress to callback if set."""
        if self._progress_callback:
            self._progress_callback(self._processed_files, self._total_files, message)

    def discover_files(self) -> List[Path]:
        """
        Discover all relevant source files in the project.
        Respects ignore patterns and only includes supported languages.
        """
        files = []
        supported_extensions = set(LanguageDetector.EXTENSION_MAP.keys())

        for root, dirs, filenames in os.walk(self.project_root):
            root_path = Path(root)

            # Filter directories
            dirs[:] = [
                d for d in dirs
                if not self._should_ignore(root_path / d)
            ]

            # Filter files
            for filename in filenames:
                file_path = root_path / filename

                if file_path.suffix.lower() in supported_extensions:
                    if not self._should_ignore(file_path):
                        files.append(file_path)

        return files

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored."""
        path_str = str(path)

        for pattern in self.ignore_patterns:
            if pattern.startswith('*'):
                # Glob pattern
                if path.match(pattern):
                    return True
            else:
                # Directory/file name
                if f'/{pattern}/' in path_str or f'/{pattern}' in path_str or path.name == pattern:
                    return True

        return False

    def map_directory(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Map the entire directory.

        Args:
            incremental: If True, only process changed files.

        Returns:
            Performance report dictionary.
        """
        self.monitor.start()

        # Discover files
        print(f"Discovering files in {self.project_root}...")
        all_files = self.discover_files()
        self._total_files = len(all_files)
        print(f"Found {len(all_files)} source files")

        if incremental:
            # Filter to changed files
            files_to_process = self._get_changed_files(all_files)
            removed_files = self._get_removed_files(all_files)

            # Remove deleted files from database
            for file_path in removed_files:
                self.db.delete_file_components(str(file_path))
                self.hash_cache.remove(str(file_path))

            print(f"Processing {len(files_to_process)} changed files, {len(removed_files)} removed")
        else:
            files_to_process = all_files

        if not files_to_process:
            print("No files to process")
            self.monitor.stop()
            return self.monitor.get_report()

        # Process files
        self._process_files(files_to_process)

        # Save hash cache
        self.hash_cache.save()

        self.monitor.stop()
        return self.monitor.get_report()

    def _get_changed_files(self, all_files: List[Path]) -> List[Path]:
        """Get list of files that need processing."""
        changed = []

        for file_path in all_files:
            try:
                stat = file_path.stat()
                mtime = stat.st_mtime
                size = stat.st_size

                if self.hash_cache.needs_update(str(file_path), mtime, size):
                    changed.append(file_path)
                else:
                    self.monitor.record_skip()
            except OSError:
                continue

        return changed

    def _get_removed_files(self, current_files: List[Path]) -> List[str]:
        """Get list of files that were removed."""
        current_set = {str(f) for f in current_files}
        cached_set = self.hash_cache.get_cached_files()
        return list(cached_set - current_set)

    def _process_files(self, files: List[Path]):
        """Process files using parallel execution."""
        total = len(files)

        # Choose execution strategy
        if total > 100 and self.use_multiprocessing:
            # Use multiprocessing for large batches
            self._process_files_multiprocess(files)
        else:
            # Use threading for smaller batches
            self._process_files_threaded(files)

    def _process_files_threaded(self, files: List[Path]):
        """Process files using thread pool."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._process_single_file, f): f
                for f in files
            }

            for i, future in enumerate(as_completed(futures)):
                file_path = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    self.monitor.record_file(success=False)

                self._processed_files = i + 1
                if (i + 1) % max(1, len(files) // 20) == 0:
                    pct = ((i + 1) / len(files)) * 100
                    print(f"  Progress: {pct:.0f}% ({i + 1}/{len(files)} files)")
                    self._report_progress(f"{pct:.0f}%")

    def _process_files_multiprocess(self, files: List[Path]):
        """Process files using process pool."""
        # Prepare file data for multiprocessing
        file_data = []
        file_stats = {}  # Track file stats for hash cache

        for f in files:
            try:
                content = f.read_text(encoding='utf-8')
                language = self.language_detector.detect(f)
                stat = f.stat()
                file_data.append((str(f), content, language))
                file_stats[str(f)] = {
                    'content': content,
                    'mtime': stat.st_mtime,
                    'size': stat.st_size
                }
            except Exception:
                self.monitor.record_file(success=False)

        # Process in parallel
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(_parse_file_worker, fd): fd[0]
                for fd in file_data
            }

            for i, future in enumerate(as_completed(futures)):
                file_path = futures[future]
                try:
                    result = future.result()
                    if result:
                        self._store_parse_result_from_dict(file_path, result)

                        # Update hash cache for successful parses
                        if file_path in file_stats:
                            stats = file_stats[file_path]
                            file_hash = hashlib.sha256(stats['content'].encode()).hexdigest()
                            self.hash_cache.set_hash(file_path, file_hash, stats['mtime'], stats['size'])
                            self.monitor.record_file(success=True, size=stats['size'])
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    self.monitor.record_file(success=False)

                self._processed_files = i + 1
                if (i + 1) % max(1, len(files) // 20) == 0:
                    pct = ((i + 1) / len(files)) * 100
                    print(f"  Progress: {pct:.0f}% ({i + 1}/{len(files)} files)")
                    self._report_progress(f"{pct:.0f}%")

    def _process_single_file(self, file_path: Path) -> bool:
        """Process a single file."""
        try:
            # Read file
            content = file_path.read_text(encoding='utf-8')
            size = len(content.encode('utf-8'))

            # Detect language
            language = self.language_detector.detect(file_path)

            if language == 'unknown':
                self.monitor.record_skip()
                return False

            # Get parser
            parser = get_parser_for_file(file_path, language)
            if not parser:
                self.monitor.record_skip()
                return False

            # Parse file
            result = parser.parse(content, str(file_path))

            # Store results
            self._store_parse_result(str(file_path), result, content, language)

            # Update hash cache
            stat = file_path.stat()
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            self.hash_cache.set_hash(str(file_path), file_hash, stat.st_mtime, stat.st_size)

            self.monitor.record_file(success=True, size=size)
            return True

        except UnicodeDecodeError:
            # Try with fallback encoding
            try:
                content = file_path.read_text(encoding='latin-1')
                return self._process_single_file_with_content(file_path, content)
            except:
                self.monitor.record_file(success=False)
                return False

        except Exception as e:
            self.monitor.record_file(success=False)
            return False

    def _process_single_file_with_content(self, file_path: Path, content: str) -> bool:
        """Process a file with pre-read content."""
        try:
            language = self.language_detector.detect(file_path)
            parser = get_parser_for_file(file_path, language)

            if not parser:
                return False

            result = parser.parse(content, str(file_path))
            self._store_parse_result(str(file_path), result, content, language)

            stat = file_path.stat()
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            self.hash_cache.set_hash(str(file_path), file_hash, stat.st_mtime, stat.st_size)

            self.monitor.record_file(success=True, size=len(content))
            return True

        except:
            return False

    def _store_parse_result(
        self,
        file_path: str,
        result: ParseResult,
        content: Optional[str] = None,
        language: Optional[str] = None
    ):
        """Store parse results in database."""
        # Delete existing components for this file
        self.db.delete_file_components(file_path)

        # Add components
        component_ids = {}
        for comp in result.components:
            comp_id = self.db.add_component(comp)
            component_ids[comp.name] = comp_id

        # Add relationships
        for rel in result.relationships:
            from_name = rel['from']
            if from_name in component_ids:
                self.db.add_relationship(
                    from_id=component_ids[from_name],
                    to_name=rel['to'],
                    rel_type=rel['type'],
                    confidence=rel.get('confidence', 1.0),
                    line_number=rel.get('line')
                )

        # Add file metadata
        if content and language:
            lines = content.count('\n') + 1
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            stat = Path(file_path).stat()

            self.db.add_file(
                path=file_path,
                language=language,
                file_hash=file_hash,
                size=stat.st_size,
                lines=lines,
                component_count=len(result.components),
                total_tokens=len(content) // 4,
                last_modified=stat.st_mtime
            )

        self.monitor.record_components(len(result.components))
        self.monitor.record_relationships(len(result.relationships))

    def _store_parse_result_from_dict(self, file_path: str, result_dict: Dict[str, Any]):
        """Store parse results from multiprocessing worker (dict format)."""
        # Delete existing components for this file
        self.db.delete_file_components(file_path)

        content = result_dict.get('content')
        language = result_dict.get('language')
        components = result_dict.get('components', [])
        relationships = result_dict.get('relationships', [])

        # Add components (reconstruct from dicts)
        component_ids = {}
        for comp_dict in components:
            comp = ComponentData(
                name=comp_dict['name'],
                type=comp_dict['type'],
                file_path=comp_dict['file_path'],
                line_start=comp_dict['line_start'],
                line_end=comp_dict.get('line_end', 0),
                signature=comp_dict.get('signature'),
                docstring=comp_dict.get('docstring'),
                parent=comp_dict.get('parent'),
                exported=comp_dict.get('exported', False),
                is_async=comp_dict.get('is_async', False),
                is_test=comp_dict.get('is_test', False),
                modifiers=comp_dict.get('modifiers', []),
                decorators=comp_dict.get('decorators', []),
                params=comp_dict.get('params', []),
                methods=comp_dict.get('methods', []),
                hooks=comp_dict.get('hooks', []),
                renders_components=comp_dict.get('renders_components', []),
                api_calls=comp_dict.get('api_calls', []),
                metadata=comp_dict.get('metadata', {}),
            )
            comp_id = self.db.add_component(comp)
            component_ids[comp.name] = comp_id

        # Add relationships
        for rel in relationships:
            from_name = rel['from']
            if from_name in component_ids:
                self.db.add_relationship(
                    from_id=component_ids[from_name],
                    to_name=rel['to'],
                    rel_type=rel['type'],
                    confidence=rel.get('confidence', 1.0),
                    line_number=rel.get('line')
                )

        # Add file metadata
        if content and language:
            lines = content.count('\n') + 1
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            stat = Path(file_path).stat()

            self.db.add_file(
                path=file_path,
                language=language,
                file_hash=file_hash,
                size=stat.st_size,
                lines=lines,
                component_count=len(components),
                total_tokens=len(content) // 4,
                last_modified=stat.st_mtime
            )

        self.monitor.record_components(len(components))
        self.monitor.record_relationships(len(relationships))

    def map_file(self, file_path: Path) -> bool:
        """Map a single file."""
        file_path = Path(file_path)

        if not file_path.is_absolute():
            file_path = self.project_root / file_path

        return self._process_single_file(file_path)

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self.db.get_stats()

    def close(self):
        """Close database connection."""
        self.hash_cache.save()
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def _parse_file_worker(file_data: Tuple[str, str, str]) -> Optional[Dict[str, Any]]:
    """
    Worker function for multiprocessing.
    Must be module-level for pickling.
    """
    file_path, content, language = file_data

    try:
        parser = get_parser_for_file(Path(file_path), language)
        if not parser:
            return None

        result = parser.parse(content, file_path)

        # Convert to serializable dict
        return {
            'components': [comp.to_dict() for comp in result.components],
            'relationships': result.relationships,
            'content': content,
            'language': language,
        }

    except Exception:
        return None
