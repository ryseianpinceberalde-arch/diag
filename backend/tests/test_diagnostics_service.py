from services.diagnostics import finding_severity, issue_context


def test_finding_severity_maps_noncritical_to_warning():
    assert finding_severity({"severity": "high"}) == "warning"
    assert finding_severity({"severity": "medium"}) == "warning"


def test_issue_context_provides_network_recommendation():
    possible_cause, recommendation = issue_context({"component": "network", "problem_type": "packet_loss_high"})
    assert "dropping packets" in possible_cause
    assert "gateway" in recommendation
