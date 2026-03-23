from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestDefinition:
    name: str
    train_maps: List[str]
    test_maps: List[str]
    obs_type: str = "relative"
    description: str = ""


class TestScenario(ABC):
    def __init__(self, name: str):
        self.name = name
        self.results = []
    
    @abstractmethod
    def get_test_definitions(self) -> List[TestDefinition]:
        pass
    
    def add_result(self, result: Dict[str, Any]):
        self.results.append(result)
    
    def get_results(self) -> List[Dict[str, Any]]:
        return self.results


class SizeGeneralizationScenario(TestScenario):
    def __init__(self):
        super().__init__("Size Generalization Test")
    
    def get_test_definitions(self) -> List[TestDefinition]:
        return [
            TestDefinition(
                name="6x6 -> 6x6 (Baseline)",
                train_maps=["configs/grid_6x6.yaml"],
                test_maps=["configs/grid_6x6.yaml"],
                description="Baseline performance on training size"
            ),
            TestDefinition(
                name="6x6 -> 7x7",
                train_maps=["configs/grid_6x6.yaml"],
                test_maps=["configs/grid_config.yaml"],
                description="Generalization to slightly larger map"
            ),
            TestDefinition(
                name="6x6 -> 8x8",
                train_maps=["configs/grid_6x6.yaml"],
                test_maps=["configs/grid_8x8.yaml"],
                description="Generalization to larger map"
            ),
            TestDefinition(
                name="6x6 -> 10x10",
                train_maps=["configs/grid_6x6.yaml"],
                test_maps=["configs/grid_10x10.yaml"],
                description="Primary generalization test"
            ),
            TestDefinition(
                name="6x6 -> 12x12",
                train_maps=["configs/grid_6x6.yaml"],
                test_maps=["configs/grid_12x12.yaml"],
                description="Stress test on much larger map"
            ),
        ]


class LayoutGeneralizationScenario(TestScenario):
    def __init__(self):
        super().__init__("Layout Generalization Test")
    
    def get_test_definitions(self) -> List[TestDefinition]:
        return [
            TestDefinition(
                name="Config -> map_1.tmx",
                train_maps=["configs/grid_config.yaml"],
                test_maps=["map_1"],
                description="Generalization to unseen TMX layout"
            ),
            TestDefinition(
                name="Config -> map_2.tmx",
                train_maps=["configs/grid_config.yaml"],
                test_maps=["map_2"],
                description="Generalization to different TMX layout"
            ),
            TestDefinition(
                name="Config -> map_3.tmx",
                train_maps=["configs/grid_config.yaml"],
                test_maps=["map_3"],
                description="Generalization to small TMX layout"
            ),
        ]


class ObsComparisonScenario(TestScenario):
    def __init__(self):
        super().__init__("Observation Type Comparison")
    
    def get_test_definitions(self) -> List[TestDefinition]:
        return [
            TestDefinition(
                name="Absolute vs Relative (7x7)",
                train_maps=["configs/grid_config.yaml"],
                test_maps=["configs/grid_config.yaml"],
                obs_type="both",
                description="Compare observation types on training map"
            ),
            TestDefinition(
                name="Absolute vs Relative (10x10)",
                train_maps=["configs/grid_config.yaml"],
                test_maps=["configs/grid_10x10.yaml"],
                obs_type="both",
                description="Compare observation types on larger map"
            ),
            TestDefinition(
                name="Absolute vs Relative (TMX)",
                train_maps=["configs/grid_config.yaml"],
                test_maps=["map_1"],
                obs_type="both",
                description="Compare observation types on TMX map"
            ),
        ]


class FullEvaluationScenario(TestScenario):
    def __init__(self):
        super().__init__("Full Evaluation Matrix")
    
    def get_test_definitions(self) -> List[TestDefinition]:
        return [
            TestDefinition(
                name="7x7 -> 7x7 (Baseline)",
                train_maps=["configs/grid_config.yaml"],
                test_maps=["configs/grid_config.yaml"],
                description="Baseline - no generalization"
            ),
            TestDefinition(
                name="7x7 -> 10x10 (Size)",
                train_maps=["configs/grid_config.yaml"],
                test_maps=["configs/grid_10x10.yaml"],
                description="Size generalization"
            ),
            TestDefinition(
                name="7x7 -> 12x12 (Stress)",
                train_maps=["configs/grid_config.yaml"],
                test_maps=["configs/grid_12x12.yaml"],
                description="Stress test"
            ),
            TestDefinition(
                name="7x7 -> map_1.tmx (Layout)",
                train_maps=["configs/grid_config.yaml"],
                test_maps=["map_1"],
                description="Layout generalization"
            ),
            TestDefinition(
                name="7x7 -> map_2.tmx (Layout)",
                train_maps=["configs/grid_config.yaml"],
                test_maps=["map_2"],
                description="Layout generalization"
            ),
        ]


def get_scenario(scenario_name: str) -> TestScenario:
    scenarios = {
        'size': SizeGeneralizationScenario,
        'layout': LayoutGeneralizationScenario,
        'obs-comparison': ObsComparisonScenario,
        'full': FullEvaluationScenario
    }
    
    if scenario_name not in scenarios:
        available = list(scenarios.keys())
        raise ValueError(f"Unknown scenario: {scenario_name}. Available: {available}")
    
    return scenarios[scenario_name]()
