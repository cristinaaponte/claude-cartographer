"""
Codebase Cartographer - Token-optimized codebase mapping for Claude Code
Copyright (c) 2025 Breach Craft - Mike Piekarski <mp@breachcraft.io>
Licensed under MIT License

Token optimization benchmarking and performance analysis.
Compares traditional approach vs optimized codebase map.
"""

import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .integration import ClaudeCodeIntegration


# Try to import tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None
    TIKTOKEN_AVAILABLE = False


@dataclass
class BenchmarkResult:
    """Result of a single benchmark operation."""
    operation: str
    traditional_tokens: int
    optimized_tokens: int
    savings_percent: float
    traditional_time_ms: float
    optimized_time_ms: float
    speedup_factor: float


class TokenOptimizationBenchmark:
    """
    Benchmark token optimization vs traditional approaches.

    Compares:
    - Traditional: Loading full file contents
    - Optimized: Using codebase map with 3-tier storage

    Usage:
        benchmark = TokenOptimizationBenchmark('/path/to/project')
        report = benchmark.run_full_benchmark()
    """

    # Claude pricing (per 1M tokens)
    CLAUDE_INPUT_PRICE = 3.00   # $3.00 per 1M input tokens
    CLAUDE_OUTPUT_PRICE = 15.00  # $15.00 per 1M output tokens

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self.claude_dir = self.project_root / '.claude-map'

        if not (self.claude_dir / 'codebase.db').exists():
            raise FileNotFoundError(
                f"Codebase map not found. Run 'claude-map init' first."
            )

        self.integration = ClaudeCodeIntegration(project_root)

        # Initialize tokenizer
        self._tokenizer = None
        if TIKTOKEN_AVAILABLE:
            try:
                self._tokenizer = tiktoken.get_encoding('cl100k_base')
            except:
                pass

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        Uses tiktoken if available, otherwise estimates (4 chars = 1 token).
        """
        if self._tokenizer:
            return len(self._tokenizer.encode(text))
        return max(len(text) // 4, 1)

    def benchmark_operation(
        self,
        operation_name: str,
        query: str,
        files_to_load: List[str],
    ) -> BenchmarkResult:
        """
        Benchmark a single operation.

        Args:
            operation_name: Name of the operation
            query: Query to run against codebase map
            files_to_load: Files that would be loaded traditionally

        Returns:
            BenchmarkResult with comparison metrics
        """
        # Traditional approach: Load full files
        traditional_start = time.time()
        traditional_content = self._simulate_traditional(files_to_load)
        traditional_time = (time.time() - traditional_start) * 1000
        traditional_tokens = self.count_tokens(traditional_content)

        # Optimized approach: Use codebase map
        optimized_start = time.time()
        optimized_content = self.integration.get_context(query, max_tokens=2000)
        optimized_time = (time.time() - optimized_start) * 1000
        optimized_tokens = self.count_tokens(optimized_content)

        # Calculate savings
        if traditional_tokens > 0:
            savings = ((traditional_tokens - optimized_tokens) / traditional_tokens) * 100
        else:
            savings = 0.0

        if optimized_time > 0:
            speedup = traditional_time / optimized_time
        else:
            speedup = 1.0

        return BenchmarkResult(
            operation=operation_name,
            traditional_tokens=traditional_tokens,
            optimized_tokens=optimized_tokens,
            savings_percent=round(savings, 1),
            traditional_time_ms=round(traditional_time, 2),
            optimized_time_ms=round(optimized_time, 2),
            speedup_factor=round(speedup, 1),
        )

    def _simulate_traditional(self, files: List[str]) -> str:
        """Simulate traditional approach of loading full files."""
        content_parts = []

        for file_pattern in files:
            # Find matching files
            if '*' in file_pattern:
                matching = list(self.project_root.glob(file_pattern))
            else:
                matching = [self.project_root / file_pattern]

            for file_path in matching[:5]:  # Limit to 5 files
                if file_path.exists() and file_path.is_file():
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        content_parts.append(f"# {file_path.name}\n{content}")
                    except:
                        pass

        return '\n\n'.join(content_parts)

    def run_full_benchmark(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Run comprehensive benchmark suite.

        Args:
            verbose: Print results as they're computed

        Returns:
            Complete benchmark report
        """
        if verbose:
            print(f"\n{'='*70}")
            print("Codebase Cartographer - Token Optimization Benchmark")
            print("Copyright (c) 2025 Breach Craft - Mike Piekarski")
            print('='*70)

        # Get database stats for test setup
        stats = self.integration.get_stats()
        total_files = stats['total_files']
        total_components = stats['total_components']

        if verbose:
            print(f"\nCodebase: {total_files} files, {total_components} components")
            print(f"Tokenizer: {'tiktoken (accurate)' if TIKTOKEN_AVAILABLE else 'estimate (4 chars/token)'}")

        # Define benchmark scenarios
        scenarios = self._get_benchmark_scenarios()

        results = []
        total_traditional = 0
        total_optimized = 0

        if verbose:
            print(f"\n{'Operation':<25} {'Traditional':>12} {'Optimized':>10} {'Savings':>10} {'Speedup':>10}")
            print('-' * 70)

        for scenario in scenarios:
            result = self.benchmark_operation(
                scenario['name'],
                scenario['query'],
                scenario['files'],
            )
            results.append(result)

            total_traditional += result.traditional_tokens
            total_optimized += result.optimized_tokens

            if verbose:
                print(
                    f"{result.operation:<25} "
                    f"{result.traditional_tokens:>12,} "
                    f"{result.optimized_tokens:>10,} "
                    f"{result.savings_percent:>9.1f}% "
                    f"{result.speedup_factor:>9.1f}x"
                )

        # Calculate totals
        if total_traditional > 0:
            total_savings = ((total_traditional - total_optimized) / total_traditional) * 100
        else:
            total_savings = 0

        if verbose:
            print('-' * 70)
            print(
                f"{'TOTAL':<25} "
                f"{total_traditional:>12,} "
                f"{total_optimized:>10,} "
                f"{total_savings:>9.1f}%"
            )

        # Cost analysis
        traditional_cost = (total_traditional / 1_000_000) * self.CLAUDE_INPUT_PRICE
        optimized_cost = (total_optimized / 1_000_000) * self.CLAUDE_INPUT_PRICE
        cost_savings = traditional_cost - optimized_cost

        if verbose:
            print(f"\n{'='*70}")
            print("Cost Analysis (Claude API pricing)")
            print('='*70)
            print(f"Traditional approach cost: ${traditional_cost:.4f}")
            print(f"Optimized approach cost:   ${optimized_cost:.4f}")
            print(f"Savings per query batch:   ${cost_savings:.4f}")
            print(f"\nProjected savings (1000 queries): ${cost_savings * 1000:.2f}")

        # Build report
        report = {
            'summary': {
                'total_files': total_files,
                'total_components': total_components,
                'traditional_tokens': total_traditional,
                'optimized_tokens': total_optimized,
                'savings_percent': round(total_savings, 1),
            },
            'operations': [
                {
                    'name': r.operation,
                    'traditional_tokens': r.traditional_tokens,
                    'optimized_tokens': r.optimized_tokens,
                    'savings_percent': r.savings_percent,
                    'speedup_factor': r.speedup_factor,
                }
                for r in results
            ],
            'cost_analysis': {
                'traditional_cost_usd': round(traditional_cost, 4),
                'optimized_cost_usd': round(optimized_cost, 4),
                'savings_per_batch_usd': round(cost_savings, 4),
                'savings_per_1000_queries_usd': round(cost_savings * 1000, 2),
            },
            'configuration': {
                'tiktoken_available': TIKTOKEN_AVAILABLE,
                'pricing': {
                    'input_per_1m': self.CLAUDE_INPUT_PRICE,
                    'output_per_1m': self.CLAUDE_OUTPUT_PRICE,
                }
            }
        }

        return report

    def _get_benchmark_scenarios(self) -> List[Dict[str, Any]]:
        """Get list of benchmark scenarios based on codebase."""
        # Get some real component names from the database
        cursor = self.integration.db.conn.execute("""
            SELECT name, file_path FROM component_index
            WHERE is_exported = 1
            ORDER BY access_count DESC
            LIMIT 5
        """)
        components = cursor.fetchall()

        # Get some file paths
        cursor = self.integration.db.conn.execute("""
            SELECT path FROM files
            ORDER BY component_count DESC
            LIMIT 5
        """)
        files = cursor.fetchall()

        scenarios = [
            {
                'name': 'Find component',
                'query': f"find {components[0]['name']}" if components else "find main",
                'files': ['**/*.py', '**/*.js'] if not files else [files[0]['path']],
            },
            {
                'name': 'Get exports',
                'query': "show exported components",
                'files': ['**/*.py', '**/*.js', '**/*.ts'],
            },
            {
                'name': 'Codebase overview',
                'query': "overview",
                'files': ['**/*.py', '**/*.js', '**/*.ts', '**/*.go'],
            },
        ]

        # Add file-specific scenarios if we have files
        if files:
            scenarios.append({
                'name': 'File dependencies',
                'query': f"dependencies {Path(files[0]['path']).name}",
                'files': [files[0]['path']],
            })

        # Add component-specific scenarios
        if components:
            scenarios.append({
                'name': 'Component detail',
                'query': f"detail {components[0]['name']}",
                'files': [components[0]['file_path']],
            })

        if len(components) > 1:
            scenarios.append({
                'name': 'Search components',
                'query': f"search {components[1]['name'][:4]}",
                'files': ['**/*.py', '**/*.js'],
            })

        return scenarios

    def close(self):
        """Close integration."""
        self.integration.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
