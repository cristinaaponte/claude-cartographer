"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

File system watcher for real-time incremental updates.
Uses watchdog library with debouncing for efficient change detection.
"""

import time
import threading
from pathlib import Path
from typing import Set, Optional, TYPE_CHECKING
from collections import deque

# Try to import watchdog
try:
    from watchdog.observers import Observer
    from watchdog.events import (
        FileSystemEventHandler,
        FileCreatedEvent,
        FileModifiedEvent,
        FileDeletedEvent,
        FileMovedEvent,
    )
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object

if TYPE_CHECKING:
    from .mapper import CodebaseMapper


class CodebaseWatcher(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """
    Watch for file changes and update the codebase map.

    Features:
    - Debouncing to batch rapid changes
    - Queue-based change processing
    - Handles create, modify, delete, move events
    - Filters to only process relevant files

    Usage:
        mapper = CodebaseMapper('/path/to/project')
        watcher = CodebaseWatcher(mapper)
        observer = watcher.start()

        # Later...
        observer.stop()
        watcher.stop()
        observer.join()
    """

    def __init__(
        self,
        mapper: 'CodebaseMapper',
        debounce_seconds: float = 0.5,
    ):
        if WATCHDOG_AVAILABLE:
            super().__init__()

        self.mapper = mapper
        self.debounce_seconds = debounce_seconds

        # Change tracking
        self._pending_changes: Set[str] = set()
        self._deleted_files: Set[str] = set()
        self._last_change_time: float = 0
        self._lock = threading.Lock()

        # Processing thread
        self._running = False
        self._process_thread: Optional[threading.Thread] = None

    def start(self) -> Optional['Observer']:
        """
        Start watching for file changes.

        Returns:
            Observer instance if successful, None if watchdog not available.
        """
        if not WATCHDOG_AVAILABLE:
            print("Warning: watchdog not installed. File watching disabled.")
            return None

        # Start processing thread
        self._running = True
        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._process_thread.start()

        # Start observer
        observer = Observer()
        observer.schedule(self, str(self.mapper.project_root), recursive=True)
        observer.start()

        print(f"Watching: {self.mapper.project_root}")
        return observer

    def stop(self):
        """Stop the watcher."""
        self._running = False
        if self._process_thread:
            self._process_thread.join(timeout=2)

    def on_created(self, event):
        """Handle file creation."""
        if not event.is_directory:
            self._queue_change(event.src_path)

    def on_modified(self, event):
        """Handle file modification."""
        if not event.is_directory:
            self._queue_change(event.src_path)

    def on_deleted(self, event):
        """Handle file deletion."""
        if not event.is_directory:
            self._queue_deletion(event.src_path)

    def on_moved(self, event):
        """Handle file move/rename."""
        if not event.is_directory:
            self._queue_deletion(event.src_path)
            self._queue_change(event.dest_path)

    def _queue_change(self, file_path: str):
        """Queue a file for processing."""
        if not self._should_process(file_path):
            return

        with self._lock:
            self._pending_changes.add(file_path)
            self._deleted_files.discard(file_path)
            self._last_change_time = time.time()

    def _queue_deletion(self, file_path: str):
        """Queue a file for deletion."""
        if not self._should_process(file_path):
            return

        with self._lock:
            self._deleted_files.add(file_path)
            self._pending_changes.discard(file_path)
            self._last_change_time = time.time()

    def _should_process(self, file_path: str) -> bool:
        """Check if a file should be processed."""
        path = Path(file_path)

        # Check extension
        if path.suffix.lower() not in self.mapper.language_detector.EXTENSION_MAP:
            return False

        # Check ignore patterns
        if self.mapper._should_ignore(path):
            return False

        # Skip temporary/editor files
        name = path.name
        if name.startswith('.') or name.startswith('~'):
            return False
        if name.endswith('.swp') or name.endswith('.tmp'):
            return False
        if name.endswith('~'):
            return False

        return True

    def _process_loop(self):
        """Background thread that processes changes after debounce."""
        while self._running:
            time.sleep(0.1)

            # Check if we have pending changes and debounce time has passed
            with self._lock:
                if not self._pending_changes and not self._deleted_files:
                    continue

                time_since_change = time.time() - self._last_change_time
                if time_since_change < self.debounce_seconds:
                    continue

                # Get changes to process
                changes = self._pending_changes.copy()
                deletions = self._deleted_files.copy()
                self._pending_changes.clear()
                self._deleted_files.clear()

            # Process outside lock
            if changes or deletions:
                self._process_batch(changes, deletions)

    def _process_batch(self, changes: Set[str], deletions: Set[str]):
        """Process a batch of file changes."""
        total = len(changes) + len(deletions)
        print(f"\nProcessing {total} file change(s)...")

        # Handle deletions
        for file_path in deletions:
            try:
                self.mapper.db.delete_file_components(file_path)
                self.mapper.hash_cache.remove(file_path)
                print(f"  - Removed: {Path(file_path).name}")
            except Exception as e:
                print(f"  - Error removing {file_path}: {e}")

        # Handle modifications/creations
        success = 0
        for file_path in changes:
            try:
                if self.mapper.map_file(Path(file_path)):
                    success += 1
                    print(f"  + Updated: {Path(file_path).name}")
            except Exception as e:
                print(f"  - Error processing {file_path}: {e}")

        # Save hash cache
        self.mapper.hash_cache.save()

        print(f"Done: {success} updated, {len(deletions)} removed")
