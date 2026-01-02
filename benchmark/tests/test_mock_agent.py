"""Mock agent tests.

Tests cover:
- All mock behaviors (perfect, empty, random, noisy)
- Deterministic behavior with seed
- Error handling for unknown behaviors
- Subset properties
"""

from __future__ import annotations

import pytest

from smi_bench.agents.mock_agent import MockAgent


def test_mock_agent_perfect_behavior() -> None:
    """Perfect behavior returns exact truth set."""
    agent = MockAgent(behavior="perfect", seed=42)

    truth_key_types = {"0x1::m::S", "0x2::m::T"}
    predicted = agent.predict_key_types(truth_key_types=truth_key_types)

    assert predicted == truth_key_types


def test_mock_agent_empty_behavior() -> None:
    """Empty behavior returns empty set."""
    agent = MockAgent(behavior="empty", seed=42)

    truth_key_types = {"0x1::m::S", "0x2::m::T"}
    predicted = agent.predict_key_types(truth_key_types=truth_key_types)

    assert predicted == set()
    assert len(predicted) == 0


def test_mock_agent_random_behavior_deterministic_with_seed() -> None:
    """Random behavior is deterministic with fixed seed."""
    agent1 = MockAgent(behavior="random", seed=123)
    agent2 = MockAgent(behavior="random", seed=123)

    truth_key_types = {"0x1::m::S", "0x2::m::T", "0x3::m::U"}

    predicted1 = agent1.predict_key_types(truth_key_types=truth_key_types)
    predicted2 = agent2.predict_key_types(truth_key_types=truth_key_types)

    # Same seed should produce same results
    assert predicted1 == predicted2


def test_mock_agent_random_behavior_different_seeds() -> None:
    """Different seeds produce different predictions."""
    agent1 = MockAgent(behavior="random", seed=1)
    agent2 = MockAgent(behavior="random", seed=2)

    truth_key_types = {"0x1::m::S"}

    predicted1 = agent1.predict_key_types(truth_key_types=truth_key_types)
    predicted2 = agent2.predict_key_types(truth_key_types=truth_key_types)

    # Different seeds should produce different results (usually)
    # But since both random with seed, they'll each be deterministic
    # and different seeds -> different results
    assert predicted1 != predicted2 or len(predicted1) != len(predicted2)


def test_mock_agent_random_subset_property() -> None:
    """Random behavior prediction is always subset of truth."""
    agent = MockAgent(behavior="random", seed=42)

    truth_key_types = {"0x1::m::S", "0x2::m::T", "0x3::m::U"}
    predicted = agent.predict_key_types(truth_key_types=truth_key_types)

    # Prediction should be subset of truth
    assert predicted.issubset(truth_key_types)


def test_mock_agent_random_subset_size_between() -> None:
    """Random behavior subset size is between 0 and len(truth)."""
    for _ in range(10):  # Test multiple times since random
        agent = MockAgent(behavior="random", seed=42)

        truth_key_types = {"0x1::m::S", "0x2::m::T", "0x3::m::U", "0x4::m::V"}
        predicted = agent.predict_key_types(truth_key_types=truth_key_types)

        # Prediction size should be valid
        assert 0 <= len(predicted) <= len(truth_key_types)


def test_mock_agent_noisy_behavior_contains_truth() -> None:
    """Noisy behavior contains all truth types."""
    agent = MockAgent(behavior="noisy", seed=42)

    truth_key_types = {"0x1::m::S", "0x2::m::T"}
    predicted = agent.predict_key_types(truth_key_types=truth_key_types)

    # All truth types should be in prediction
    assert truth_key_types.issubset(predicted)


def test_mock_agent_noisy_behavior_adds_junk() -> None:
    """Noisy behavior adds junk types (5 random strings)."""
    agent = MockAgent(behavior="noisy", seed=42)

    truth_key_types = {"0x1::m::S"}
    predicted = agent.predict_key_types(truth_key_types=truth_key_types)

    # Prediction should contain all truth types plus junk
    assert "0x1::m::S" in predicted
    # Junk types should be present (5 junk entries)
    # Count of junk types
    junk_count = len([t for t in predicted if t not in truth_key_types])
    assert junk_count == 5


def test_mock_agent_noisy_behavior_junk_pattern() -> None:
    """Noisy behavior junk has expected pattern."""
    agent = MockAgent(behavior="noisy", seed=123)

    truth_key_types = {"0x1::m::S"}
    predicted = agent.predict_key_types(truth_key_types=truth_key_types)

    # Junk types should match pattern
    junk_types = [t for t in predicted if t not in truth_key_types]

    # Should have exactly 5 junk types (as per implementation)
    assert len(junk_types) == 5

    # All junk types should match pattern "0xdead::1234::Fake"
    for junk_type in junk_types:
        # Format should be "0xdead::<number>::Fake"
        assert "::Fake" in junk_type
        assert "0xdead::" in junk_type


def test_mock_agent_unknown_behavior_raises_valueerror() -> None:
    """Unknown behavior raises ValueError."""
    agent = MockAgent(behavior="unknown", seed=42)

    truth_key_types = {"0x1::m::S"}

    with pytest.raises(ValueError) as exc_info:
        agent.predict_key_types(truth_key_types=truth_key_types)

    assert "unknown" in str(exc_info.value).lower()


def test_mock_agent_default_seed() -> None:
    """Default seed (0) produces deterministic results."""
    agent1 = MockAgent(behavior="perfect", seed=0)
    agent2 = MockAgent(behavior="perfect", seed=0)

    truth_key_types = {"0x1::m::S"}

    predicted1 = agent1.predict_key_types(truth_key_types=truth_key_types)
    predicted2 = agent2.predict_key_types(truth_key_types=truth_key_types)

    # Same default seed should produce same results
    assert predicted1 == predicted2


def test_mock_agent_empty_truth() -> None:
    """Behavior handles empty truth key types."""
    agent = MockAgent(behavior="perfect", seed=42)

    truth_key_types = set()
    predicted = agent.predict_key_types(truth_key_types=truth_key_types)

    # Empty truth should produce empty prediction
    assert predicted == set()


def test_mock_agent_large_truth_set() -> None:
    """Behavior handles large truth sets (100+ types)."""
    agent = MockAgent(behavior="perfect", seed=42)

    truth_key_types = {f"0x{i}::m::S{i}" for i in range(100)}
    predicted = agent.predict_key_types(truth_key_types=truth_key_types)

    assert predicted == truth_key_types
    assert len(predicted) == 100
