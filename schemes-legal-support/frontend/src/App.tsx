import { useEffect, useState } from "react";

import "./App.css";
import { AdminApp } from "./admin/AdminApp";
import { ApiError, postMatch } from "./api";
import { IntakeForm } from "./components/IntakeForm";
import { ResultsList } from "./components/ResultsList";
import type { MatchedScheme, UserProfile } from "./types";

type Screen = "form" | "results";

/** Bare hash routing — `#/admin` shows the internal admin tool. */
function isAdminHash(): boolean {
  return window.location.hash
    .replace(/^#\/?/, "")
    .toLowerCase()
    .startsWith("admin");
}

function useAdminRoute(): boolean {
  const [admin, setAdmin] = useState(isAdminHash);
  useEffect(() => {
    const onChange = () => setAdmin(isAdminHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return admin;
}

export default function App() {
  const admin = useAdminRoute();
  const [screen, setScreen] = useState<Screen>("form");
  const [profile, setProfile] = useState<Partial<UserProfile>>({});
  const [results, setResults] = useState<MatchedScheme[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(next: Partial<UserProfile>) {
    setProfile(next);
    setSubmitting(true);
    setErrorMessage(null);
    try {
      const matches = await postMatch(next);
      setResults(matches);
      setScreen("results");
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Something went wrong while searching. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (admin) return <AdminApp />;

  return (
    <div className="app">
      <header className="app-header">
        <h1>Find government schemes for you</h1>
        <p className="tagline">
          Answer a few optional questions to see which Indian government schemes
          you may qualify for. Nothing is saved, and no sign-in is needed.
        </p>
      </header>

      {screen === "form" ? (
        <IntakeForm
          initialProfile={profile}
          submitting={submitting}
          errorMessage={errorMessage}
          onSubmit={handleSubmit}
        />
      ) : (
        <ResultsList results={results} onRefine={() => setScreen("form")} />
      )}

      <footer className="app-footer">
        <p>
          Eligibility shown here is an automated estimate, not an official
          decision. Always confirm on the scheme&rsquo;s official government
          website.
        </p>
        <p>
          <a className="admin-link" href="#/admin">
            Scheme admin →
          </a>
        </p>
      </footer>
    </div>
  );
}
