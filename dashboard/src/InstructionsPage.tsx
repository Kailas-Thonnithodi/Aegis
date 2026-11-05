import { api } from "./api";
import { usePolling } from "./hooks";

export function InstructionsPage() {
  const instructions = usePolling(api.getInstructions, null).data;

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Agent instructions</h1>
          <p className="muted">
            What the Aegis Agent follows on every claim. Read only.
          </p>
        </div>
      </header>
      <section className="panel">
        {instructions ? (
          <pre className="instructions">{instructions.text}</pre>
        ) : (
          <p className="muted">Loading the instructions.</p>
        )}
      </section>
    </>
  );
}
