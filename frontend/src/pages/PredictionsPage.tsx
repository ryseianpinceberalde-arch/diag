import { BrainCircuit, Eye } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { LoadingBlock } from "../components/LoadingBlock";
import { RiskScoreIndicator } from "../components/RiskScoreIndicator";
import { StatusBadge } from "../components/StatusBadge";
import { apiFetch } from "../lib/api";
import { Computer } from "../types/models";

export function PredictionsPage() {
  const [computers, setComputers] = useState<Computer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<{ items: Computer[] }>("/computers")
      .then((data) => setComputers(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const ranked = [...computers].sort((a, b) => (b.latest_prediction?.risk_score ?? 0) - (a.latest_prediction?.risk_score ?? 0));

  return (
    <div className="page">
      <header className="page-header">
        <h1>Failure Risk Predictions</h1>
        <p>Explainable scoring is used until labeled failure data exists.</p>
      </header>
      {error && <p className="error">{error}</p>}
      {loading ? <LoadingBlock /> : ranked.length === 0 ? <p className="empty">No predictions are available yet.</p> : (
        <div className="prediction-grid">
          {ranked.map((computer) => {
            const prediction = computer.latest_prediction;
            return (
              <section className="prediction-card" key={computer.id}>
                <div className="prediction-main">
                  <div className="prediction-icon"><BrainCircuit size={22} /></div>
                  <div>
                    <strong>{computer.computer_name}</strong>
                    <span>{prediction?.suspected_component ?? "system"} · {computer.device_id.slice(0, 12)}</span>
                  </div>
                </div>
                <RiskScoreIndicator score={prediction?.risk_score ?? 0} />
                <p>{prediction?.recommended_action ?? "Run analysis after readings are available."}</p>
                <div className="prediction-actions">
                  <StatusBadge value={prediction?.risk_level ?? "low"} />
                  <Link className="text-action" to={`/computers/${computer.id}`}><Eye size={16} /> Details</Link>
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
