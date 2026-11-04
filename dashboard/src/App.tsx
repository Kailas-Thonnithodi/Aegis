import { useEffect, useState } from "react";

type Health = "checking" | "up" | "down";

const messages: Record<Health, string> = {
  checking: "Checking the backend.",
  up: "The backend is up.",
  down: "The backend is down.",
};

export function App() {
  const [health, setHealth] = useState<Health>("checking");

  useEffect(() => {
    fetch("/api/health")
      .then((response) => {
        setHealth(response.ok ? "up" : "down");
      })
      .catch(() => {
        setHealth("down");
      });
  }, []);

  return (
    <main>
      <h1>Aegis Claims</h1>
      <p className="tagline">Travel claims, decided with care</p>
      <section className="panel">
        <h2>Backend</h2>
        <p className={`status status-${health}`}>{messages[health]}</p>
      </section>
    </main>
  );
}
