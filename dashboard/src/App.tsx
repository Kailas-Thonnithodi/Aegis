import { ChecksPage } from "./ChecksPage";
import { ClaimPage } from "./ClaimPage";
import { useHash } from "./hooks";
import { InstructionsPage } from "./InstructionsPage";
import { QueuePage } from "./QueuePage";

function Page({ hash }: Readonly<{ hash: string }>) {
  if (hash === "#/instructions") return <InstructionsPage />;
  if (hash === "#/checks") return <ChecksPage />;
  const claimId = /^#\/claims\/([\w-]+)$/.exec(hash)?.[1];
  if (claimId) return <ClaimPage key={claimId} claimId={claimId} />;
  return <QueuePage />;
}

function section(hash: string): string {
  if (hash.startsWith("#/instructions")) return "instructions";
  if (hash.startsWith("#/checks")) return "checks";
  return "queue";
}

export function App() {
  const hash = useHash();
  const current = section(hash);
  const links = [
    { href: "#/", name: "Queue", section: "queue" },
    { href: "#/checks", name: "Checks", section: "checks" },
    {
      href: "#/instructions",
      name: "Agent instructions",
      section: "instructions",
    },
  ];

  return (
    <>
      <header className="top">
        <div className="top-inner">
          <a className="brand" href="#/">
            Aegis Claims
          </a>
          <span className="tagline">Travel claims, decided with care</span>
          <nav aria-label="Main">
            {links.map((link) => (
              <a
                key={link.href}
                href={link.href}
                aria-current={current === link.section ? "page" : undefined}
              >
                {link.name}
              </a>
            ))}
          </nav>
        </div>
      </header>
      <main>
        <Page hash={hash} />
      </main>
    </>
  );
}
