"""Integration tests for test scenarios."""

import pytest
import yaml
from pathlib import Path


class TestScenarios:
    """Test scenario validation."""
    
    def test_scenario_a_variants_exist(self):
        """Test that Scenario A variants exist."""
        scenario_dir = Path(__file__).parent.parent / "scenarios" / "scenario_a_oom"
        
        assert scenario_dir.exists()
        
        variants = list(scenario_dir.glob("variant_*.yaml"))
        assert len(variants) >= 3, "Should have at least 3 variants"
    
    def test_scenario_b_exists(self):
        """Test that Scenario B exists."""
        scenario_dir = Path(__file__).parent.parent / "scenarios" / "scenario_b_service"
        
        assert scenario_dir.exists()
        
        broken_service = scenario_dir / "broken_service.yaml"
        assert broken_service.exists()
    
    def test_yaml_validity(self):
        """Test that scenario YAML files are valid."""
        scenarios_dir = Path(__file__).parent.parent / "scenarios"
        
        for yaml_file in scenarios_dir.rglob("*.yaml"):
            if "kustomization" in yaml_file.name:
                continue
            
            with open(yaml_file) as f:
                try:
                    data = yaml.safe_load(f)
                    assert data is not None, f"Empty YAML: {yaml_file}"
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {yaml_file}: {e}")
    
    def test_scenario_a_oom_structure(self):
        """Test Scenario A structure."""
        variant_1 = Path(__file__).parent.parent / "scenarios" / "scenario_a_oom" / "variant_1_memory_limit_low.yaml"
        
        if variant_1.exists():
            with open(variant_1) as f:
                data = yaml.safe_load(f)
                assert data["kind"] == "Deployment"
                assert "spec" in data
                assert "containers" in data["spec"]["template"]["spec"]
    
    def test_scenario_b_service_structure(self):
        """Test Scenario B structure."""
        broken_service = Path(__file__).parent.parent / "scenarios" / "scenario_b_service" / "broken_service.yaml"
        
        if broken_service.exists():
            with open(broken_service) as f:
                docs = list(yaml.safe_load_all(f))
                # Should have Deployment and Service
                kinds = [doc.get("kind") for doc in docs]
                assert "Deployment" in kinds
                assert "Service" in kinds

