"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Session token tracking - tracks tokens saved during a Claude Code session.
Includes performance metrics: query time and cache hit rate.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class QueryRecord:
    """Record of a single query."""
    timestamp: float
    query_type: str  # find, query, show, exports, etc.
    query: str
    optimized_tokens: int
    traditional_tokens: int  # Estimated if we had loaded full files
    tokens_saved: int
    files_avoided: int  # Number of files we didn't have to load


@dataclass
class SessionStats:
    """Cumulative session statistics."""
    session_id: str
    started_at: float
    queries: List[QueryRecord] = field(default_factory=list)
    total_optimized_tokens: int = 0
    total_traditional_tokens: int = 0
    total_tokens_saved: int = 0
    total_files_avoided: int = 0
    _query_count: int = 0  # Persisted count (queries list may be empty when loaded)
    # Performance metrics
    total_query_time_ms: float = 0.0
    total_cache_hits: int = 0
    total_cache_misses: int = 0

    @property
    def query_count(self) -> int:
        """Get query count (uses persisted count which accumulates across process invocations)."""
        return self._query_count

    @property
    def savings_percent(self) -> float:
        if self.total_traditional_tokens > 0:
            return (self.total_tokens_saved / self.total_traditional_tokens) * 100
        return 0.0

    @property
    def cost_saved_usd(self) -> float:
        """Estimated cost saved (Claude API pricing: $3/1M input tokens)."""
        return (self.total_tokens_saved / 1_000_000) * 3.00

    @property
    def avg_query_time_ms(self) -> float:
        """Average query time in milliseconds."""
        if self._query_count > 0:
            return self.total_query_time_ms / self._query_count
        return 0.0

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as percentage."""
        total = self.total_cache_hits + self.total_cache_misses
        if total > 0:
            return (self.total_cache_hits / total) * 100
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'started_at': self.started_at,
            'duration_seconds': time.time() - self.started_at,
            'query_count': self.query_count,
            'total_optimized_tokens': self.total_optimized_tokens,
            'total_traditional_tokens': self.total_traditional_tokens,
            'total_tokens_saved': self.total_tokens_saved,
            'savings_percent': round(self.savings_percent, 1),
            'cost_saved_usd': round(self.cost_saved_usd, 4),
            'total_files_avoided': self.total_files_avoided,
            # Performance metrics
            'total_query_time_ms': round(self.total_query_time_ms, 2),
            'avg_query_time_ms': round(self.avg_query_time_ms, 2),
            'total_cache_hits': self.total_cache_hits,
            'total_cache_misses': self.total_cache_misses,
            'cache_hit_rate': round(self.cache_hit_rate, 1),
        }


class SessionTracker:
    """
    Track token savings during a Claude Code session.

    Maintains a running tally of:
    - Queries made via cartographer
    - Tokens used (optimized)
    - Tokens that would have been used (traditional)
    - Cumulative savings

    Usage:
        tracker = SessionTracker('/path/to/project')
        tracker.record_query('find', 'UserProfile', optimized=150, traditional=12000)
        print(tracker.get_summary())
    """

    # Estimates for traditional approach token costs
    TRADITIONAL_ESTIMATES = {
        'find': 15000,      # Loading ~3-5 files to find a component
        'query': 20000,     # Natural language query typically needs multiple files
        'show': 8000,       # Single file load
        'exports': 30000,   # Need to scan many files for exports
        'dependencies': 25000,  # Dependency analysis needs multiple files
        'calls': 40000,     # Call chain analysis is expensive
        'detail': 10000,    # Detailed component info
        'search': 25000,    # Search across codebase
    }

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self.cache_dir = self.project_root / '.claude-map' / 'cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.session_file = self.cache_dir / 'current_session.json'
        self.history_file = self.cache_dir / 'session_history.json'

        # Load or create session
        self.stats = self._load_or_create_session()

    def _load_or_create_session(self) -> SessionStats:
        """Load existing session or create new one."""
        if self.session_file.exists():
            try:
                data = json.loads(self.session_file.read_text())
                # Check if session is recent (within 4 hours)
                if time.time() - data.get('started_at', 0) < 14400:
                    stats = SessionStats(
                        session_id=data['session_id'],
                        started_at=data['started_at'],
                        total_optimized_tokens=data.get('total_optimized_tokens', 0),
                        total_traditional_tokens=data.get('total_traditional_tokens', 0),
                        total_tokens_saved=data.get('total_tokens_saved', 0),
                        total_files_avoided=data.get('total_files_avoided', 0),
                        _query_count=data.get('query_count', 0),
                        total_query_time_ms=data.get('total_query_time_ms', 0.0),
                        total_cache_hits=data.get('total_cache_hits', 0),
                        total_cache_misses=data.get('total_cache_misses', 0),
                    )
                    return stats
            except:
                pass

        # Create new session
        return SessionStats(
            session_id=datetime.now().strftime('%Y%m%d_%H%M%S'),
            started_at=time.time(),
        )

    def record_query(
        self,
        query_type: str,
        query: str,
        optimized_tokens: int,
        traditional_tokens: Optional[int] = None,
        files_avoided: int = 0,
        query_time_ms: float = 0.0,
        cache_hit: Optional[bool] = None,
    ):
        """
        Record a query and its token usage.

        Args:
            query_type: Type of query (find, query, show, etc.)
            query: The actual query string
            optimized_tokens: Tokens actually used
            traditional_tokens: Tokens that would have been used (estimated if None)
            files_avoided: Number of files we didn't have to load
            query_time_ms: Time taken for the query in milliseconds
            cache_hit: Whether the query hit the cache (None if not tracked)
        """
        # Estimate traditional tokens if not provided
        if traditional_tokens is None:
            traditional_tokens = self.TRADITIONAL_ESTIMATES.get(query_type, 15000)

        tokens_saved = max(0, traditional_tokens - optimized_tokens)

        record = QueryRecord(
            timestamp=time.time(),
            query_type=query_type,
            query=query[:100],  # Truncate long queries
            optimized_tokens=optimized_tokens,
            traditional_tokens=traditional_tokens,
            tokens_saved=tokens_saved,
            files_avoided=files_avoided,
        )

        self.stats.queries.append(record)
        self.stats._query_count += 1
        self.stats.total_optimized_tokens += optimized_tokens
        self.stats.total_traditional_tokens += traditional_tokens
        self.stats.total_tokens_saved += tokens_saved
        self.stats.total_files_avoided += files_avoided
        self.stats.total_query_time_ms += query_time_ms

        # Track cache hits/misses
        if cache_hit is not None:
            if cache_hit:
                self.stats.total_cache_hits += 1
            else:
                self.stats.total_cache_misses += 1

        # Save session
        self._save_session()

    def _save_session(self):
        """Save current session to disk."""
        try:
            self.session_file.write_text(json.dumps(self.stats.to_dict(), indent=2))
        except:
            pass

    def get_summary(self, verbose: bool = False) -> str:
        """Get formatted summary of session savings."""
        lines = [
            "",
            "=" * 50,
            "Session Token Savings",
            "=" * 50,
            f"Queries:          {self.stats.query_count}",
            f"Tokens used:      {self.stats.total_optimized_tokens:,}",
            f"Traditional est:  {self.stats.total_traditional_tokens:,}",
            f"Tokens saved:     {self.stats.total_tokens_saved:,}",
            f"Savings:          {self.stats.savings_percent:.1f}%",
            f"Cost saved:       ${self.stats.cost_saved_usd:.4f}",
        ]

        if self.stats.total_files_avoided > 0:
            lines.append(f"Files avoided:    {self.stats.total_files_avoided}")

        # Performance metrics
        if self.stats.total_query_time_ms > 0:
            lines.append(f"Avg query time:   {self.stats.avg_query_time_ms:.2f}ms")

        if self.stats.total_cache_hits + self.stats.total_cache_misses > 0:
            lines.append(f"Cache hit rate:   {self.stats.cache_hit_rate:.1f}%")

        if verbose and self.stats.queries:
            lines.append("")
            lines.append("Recent queries:")
            for q in self.stats.queries[-5:]:
                lines.append(f"  {q.query_type}: saved {q.tokens_saved:,} tokens")

        lines.append("=" * 50)

        return '\n'.join(lines)

    def get_inline_summary(self) -> str:
        """Get short inline summary for CLI output."""
        if self.stats.total_tokens_saved > 0:
            return (
                f"[Session: {self.stats.total_tokens_saved:,} tokens saved "
                f"({self.stats.savings_percent:.0f}%), "
                f"${self.stats.cost_saved_usd:.4f} saved]"
            )
        return ""

    def end_session(self):
        """End session and archive to history."""
        if not self.stats.queries:
            return

        # Archive to history
        try:
            history = []
            if self.history_file.exists():
                history = json.loads(self.history_file.read_text())

            history.append(self.stats.to_dict())

            # Keep last 100 sessions
            history = history[-100:]

            self.history_file.write_text(json.dumps(history, indent=2))
        except:
            pass

        # Clear current session
        try:
            self.session_file.unlink()
        except:
            pass

    def get_lifetime_stats(self) -> Dict[str, Any]:
        """Get lifetime statistics across all sessions."""
        total_saved = self.stats.total_tokens_saved
        total_queries = len(self.stats.queries)

        try:
            if self.history_file.exists():
                history = json.loads(self.history_file.read_text())
                for session in history:
                    total_saved += session.get('total_tokens_saved', 0)
                    total_queries += session.get('query_count', 0)
        except:
            pass

        return {
            'lifetime_tokens_saved': total_saved,
            'lifetime_queries': total_queries,
            'lifetime_cost_saved_usd': round((total_saved / 1_000_000) * 3.00, 2),
        }
