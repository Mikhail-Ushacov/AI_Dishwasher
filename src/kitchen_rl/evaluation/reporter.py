from typing import Dict, Any, Optional
from .metrics import AggregatedMetrics


class EvaluationReporter:
    SEPARATOR_WIDE = "=" * 70
    SEPARATOR_NARROW = "-" * 70
    
    @staticmethod
    def print_header(title: str):
        print(f"\n{EvaluationReporter.SEPARATOR_WIDE}")
        print(f"EVALUATION: {title}")
        print(EvaluationReporter.SEPARATOR_WIDE)
    
    @staticmethod
    def print_subheader(title: str):
        print(f"\n{EvaluationReporter.SEPARATOR_NARROW}")
        print(f"{title}")
        print(EvaluationReporter.SEPARATOR_NARROW)
    
    @staticmethod
    def print_config(config: Dict[str, Any]):
        for key, value in config.items():
            print(f"{key}: {value}")
        print()
    
    @staticmethod
    def print_test_info(
        train_map: str,
        test_map: str,
        obs_type: str = "N/A",
        episodes: int = 10
    ):
        print(f"Train Map: {train_map}")
        print(f"Test Map: {test_map}")
        if obs_type != "N/A":
            print(f"Observation Type: {obs_type}")
        print(f"Episodes: {episodes}")
        print()
    
    @staticmethod
    def print_metrics(
        metrics: AggregatedMetrics,
        baseline: Optional[AggregatedMetrics] = None,
        show_std: bool = True
    ):
        if baseline:
            from .metrics import compare_metrics
            improvements = compare_metrics(baseline, metrics)
            
            def format_change(value: float) -> str:
                if value > 0:
                    return f"↑{value:.1f}%"
                elif value < 0:
                    return f"↓{abs(value):.1f}%"
                else:
                    return "0.0%"
            
            print(f"  Success Rate:    {metrics.success_rate:5.1%} ± {metrics.success_rate_std:5.1%}   [{format_change(improvements['success_rate_change'])} from baseline]")
            print(f"  Avg Reward:      {metrics.avg_reward:6.1f} ± {metrics.avg_reward_std:5.1f}      [{format_change(improvements['reward_change'])} from baseline]")
            print(f"  Avg Steps:       {metrics.avg_steps:6.1f} ± {metrics.avg_steps_std:5.1f}        [{format_change(improvements['steps_change'])} from baseline]")
            print(f"  Order Efficiency: {metrics.order_efficiency:5.1%} ± {metrics.order_efficiency_std:5.1%}")
        else:
            if show_std:
                print(f"  Success Rate:    {metrics.success_rate:5.1%} ± {metrics.success_rate_std:5.1%}")
                print(f"  Avg Reward:      {metrics.avg_reward:6.1f} ± {metrics.avg_reward_std:5.1f}")
                print(f"  Avg Steps:       {metrics.avg_steps:6.1f} ± {metrics.avg_steps_std:5.1f}")
                print(f"  Order Efficiency: {metrics.order_efficiency:5.1%} ± {metrics.order_efficiency_std:5.1%}")
            else:
                print(f"  Success Rate:    {metrics.success_rate:5.1%}")
                print(f"  Avg Reward:      {metrics.avg_reward:6.1f}")
                print(f"  Avg Steps:       {metrics.avg_steps:6.1f}")
                print(f"  Order Efficiency: {metrics.order_efficiency:5.1%}")
    
    @staticmethod
    def print_generalization_score(score: float):
        if score >= 80:
            status = "[OK]"
            label = "Excellent"
        elif score >= 60:
            status = "[OK]"
            label = "Good"
        elif score >= 40:
            status = "[!]"
            label = "Fair"
        else:
            status = "[X]"
            label = "Poor"
        
        print(f"\n  Generalization Score: {score:5.1f}% {status} ({label})")
    
    @staticmethod
    def print_summary_table(results: list):
        print(f"\n{EvaluationReporter.SEPARATOR_WIDE}")
        print("SUMMARY")
        print(EvaluationReporter.SEPARATOR_WIDE)
        print(f"| {'Test Case':<20} | {'Success Rate':<14} | {'Gen. Score':<18} |")
        print(f"|{'-'*22}|{'-'*16}|{'-'*20}|")
        
        for result in results:
            test_name = result.get('test_name', 'Unknown')
            success_rate = result.get('success_rate', 0.0)
            gen_score = result.get('gen_score', 100.0)
            
            if gen_score == 100.0:
                gen_score_str = f"{gen_score:5.1f}% (baseline)"
            else:
                gen_score_str = f"{gen_score:5.1f}%"
            
            print(f"| {test_name:<20} | {success_rate:5.1%}        | {gen_score_str:<18} |")
    
    @staticmethod
    def print_insights(insights: list):
        print(f"\nKey Insights:")
        for insight in insights:
            print(f"{insight}")
    
    @staticmethod
    def print_progress(current: int, total: int, prefix: str = "Running"):
        percent = (current / total) * 100
        bar_length = 30
        filled = int(bar_length * current / total)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"\r{prefix}: [{bar}] {current}/{total} ({percent:.1f}%)", end="", flush=True)
        if current == total:
            print()
    
    @staticmethod
    def print_error(message: str):
        print(f"\n[ERROR] {message}")
    
    @staticmethod
    def print_success(message: str):
        print(f"\n[SUCCESS] {message}")
    
    @staticmethod
    def print_episode_result(ep: int, reward: float, steps: int, success: bool):
        status = "[OK]" if success else "[FAIL]"
        print(f"  Episode {ep:2d}: {reward:7.1f} ({steps:3d} steps) {status}")
