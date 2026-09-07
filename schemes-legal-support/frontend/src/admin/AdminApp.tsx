/*
 * ⚠️  SECURITY — NO AUTHENTICATION.
 *
 * This admin screen is reachable by anyone who opens the `#/admin` hash, and
 * the backend's POST/PUT /schemes endpoints are likewise unauthenticated. It
 * is an internal data-review tool only. Before ANY real deployment this MUST
 * be placed behind authentication + authorization, and the write endpoints
 * must be protected server-side (a UI check is not a control).
 */
import { useState } from "react";

import type { Scheme } from "../types";
import { SchemeForm } from "./SchemeForm";
import { SchemeList } from "./SchemeList";

type View =
  | { kind: "list" }
  | { kind: "create" }
  | { kind: "edit"; scheme: Scheme };

export function AdminApp() {
  const [view, setView] = useState<View>({ kind: "list" });
  const [reloadKey, setReloadKey] = useState(0);

  return (
    <div className="admin">
      <header className="admin-header">
        <div>
          <h1>Scheme admin</h1>
          <p className="admin-warn">
            ⚠️ No authentication — internal review tool. Add auth before
            deploying.
          </p>
        </div>
        <a href="#/" className="btn-link">
          ← Public site
        </a>
      </header>

      {view.kind === "list" ? (
        <>
          <div className="admin-toolbar">
            <button
              type="button"
              className="btn-primary"
              onClick={() => setView({ kind: "create" })}
            >
              + New scheme
            </button>
          </div>
          <SchemeList
            reloadKey={reloadKey}
            onEdit={(scheme) => setView({ kind: "edit", scheme })}
          />
        </>
      ) : (
        <SchemeForm
          mode={view.kind}
          initial={view.kind === "edit" ? view.scheme : undefined}
          onCancel={() => setView({ kind: "list" })}
          onSaved={() => {
            setReloadKey((k) => k + 1);
            setView({ kind: "list" });
          }}
        />
      )}
    </div>
  );
}
