import { ClaimPage } from "./ClaimPage";
import { useHash } from "./hooks";
import { InstructionsPage } from "./InstructionsPage";
import { QueuePage } from "./QueuePage";

function Page({ hash }: Readonly<{ hash: string }>) {
  if (hash === "#/instructions") return <InstructionsPage />;
  const claimId = /^#\/claims\/([\w-]+)$/.exec(hash)?.[1];
  if (claimId) return <ClaimPage key={claimId} claimId={claimId} />;
  return <QueuePage />;
}

export function App() {
  const hash = useHash();
  const onInstructions = hash === "#/instructions";

  return (
    <>
      <header className="top">
        <div className="top-inner">
          <a className="brand" href="#/">
            Aegis Claims
          </a>
          <span className="tagline">Travel claims, decided with care</span>
          <nav aria-label="Main">
            <a href="#/" aria-current={onInstructions ? undefined : "page"}>
              Queue
            </a>
            <a
              href="#/instructions"
              aria-current={onInstructions ? "page" : undefined}
            >
              Agent instructions
            </a>
          </nav>
        </div>
      </header>
      <main>
        <Page hash={hash} />
      </main>
    </>
  );
}
