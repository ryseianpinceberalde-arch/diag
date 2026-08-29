import { Building2, MapPin, PlusCircle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { LoadingBlock } from "../components/LoadingBlock";
import { apiFetch } from "../lib/api";
import { Department, Location } from "../types/models";

export function OrganizationPage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [departmentName, setDepartmentName] = useState("");
  const [locationName, setLocationName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    setLoading(true);
    try {
      const [departmentData, locationData] = await Promise.all([
        apiFetch<{ items: Department[] }>("/departments"),
        apiFetch<{ items: Location[] }>("/locations")
      ]);
      setDepartments(departmentData.items);
      setLocations(locationData.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load organization data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createDepartment() {
    if (!departmentName.trim()) return;
    await apiFetch("/departments", { method: "POST", body: JSON.stringify({ name: departmentName.trim() }) });
    setDepartmentName("");
    await load();
  }

  async function createLocation() {
    if (!locationName.trim()) return;
    await apiFetch("/locations", { method: "POST", body: JSON.stringify({ name: locationName.trim() }) });
    setLocationName("");
    await load();
  }

  return (
    <div className="page">
      <header className="page-header row">
        <div>
          <h1>Organization</h1>
          <p>Departments and locations used to classify devices, reports, and repair ownership.</p>
        </div>
        <button className="secondary" onClick={load}><RefreshCw size={16} /> Refresh</button>
      </header>
      {error && <p className="error">{error}</p>}
      {loading ? <LoadingBlock /> : (
        <div className="split">
          <section className="panel">
            <h2><Building2 size={18} /> Departments</h2>
            <div className="toolbar">
              <input value={departmentName} onChange={(event) => setDepartmentName(event.target.value)} placeholder="Department name" aria-label="Department name" />
              <button onClick={createDepartment}><PlusCircle size={16} /> Add</button>
            </div>
            <div className="stack">
              {departments.length === 0 ? <p className="empty">No departments have been created.</p> : departments.map((department) => (
                <article className="list-item" key={department.id}>
                  <Building2 size={18} />
                  <strong>{department.name}</strong>
                  <span>{department.description ?? "No description"}</span>
                </article>
              ))}
            </div>
          </section>
          <section className="panel">
            <h2><MapPin size={18} /> Locations</h2>
            <div className="toolbar">
              <input value={locationName} onChange={(event) => setLocationName(event.target.value)} placeholder="Location name" aria-label="Location name" />
              <button onClick={createLocation}><PlusCircle size={16} /> Add</button>
            </div>
            <div className="stack">
              {locations.length === 0 ? <p className="empty">No locations have been created.</p> : locations.map((location) => (
                <article className="list-item" key={location.id}>
                  <MapPin size={18} />
                  <strong>{location.name}</strong>
                  <span>{[location.building, location.room].filter(Boolean).join(" / ") || location.description || "No details"}</span>
                </article>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
