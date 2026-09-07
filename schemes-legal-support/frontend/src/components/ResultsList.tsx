import { describeLeaf, isLeaf, joinList } from "../format";
import type { ConditionNode, MatchedScheme } from "../types";

function ConditionView({ node }: { node: ConditionNode }) {
  if (isLeaf(node)) {
    return <li>{describeLeaf(node)}</li>;
  }
  if (node.op === "NOT") {
    return (
      <li>
        Must <strong>not</strong> match:
        <ul>
          <ConditionView node={node.child} />
        </ul>
      </li>
    );
  }
  return (
    <li>
      {node.op === "AND" ? "All of these:" : "Any one of these:"}
      <ul>
        {node.children.map((child, index) => (
          <ConditionView key={index} node={child} />
        ))}
      </ul>
    </li>
  );
}

function jurisdictionLabel(scheme: MatchedScheme): string {
  if (scheme.level === "State" && scheme.state) {
    return `State · ${scheme.state.replace(/_/g, " ")}`;
  }
  return "Central";
}

function SchemeCard({ scheme }: { scheme: MatchedScheme }) {
  const isLikely = scheme.bucket === "likely_eligible";

  return (
    <article className={`card card-${scheme.bucket}`}>
      <header className="card-head">
        <div className="card-headings">
          <span className={`status status-${scheme.bucket}`}>
            {isLikely
              ? "You may be eligible"
              : "You might be eligible — more details needed"}
          </span>
          <h3>{scheme.name}</h3>
          <p className="card-summary">{scheme.short_summary}</p>
        </div>
        <span className="badge">{jurisdictionLabel(scheme)}</span>
      </header>

      <p className="reasoning">{scheme.reasoning}</p>

      {!isLikely && scheme.unknown_conditions.length > 0 ? (
        <p className="missing">
          <strong>Add your {joinList(scheme.unknown_conditions)}</strong> to see
          if this applies to you.
        </p>
      ) : null}

      <p className="benefits">
        <span className="field-label">What you get</span>
        {scheme.benefits}
      </p>

      <details className="details">
        <summary>View eligibility, documents &amp; how to apply</summary>
        <div className="details-body">
          <section>
            <h4>Eligibility criteria</h4>
            <ul className="tree">
              <ConditionView node={scheme.eligibility.hard} />
            </ul>
            {scheme.eligibility.soft ? (
              <>
                <p className="tree-note">
                  Given priority (does not affect whether you qualify):
                </p>
                <ul className="tree">
                  <ConditionView node={scheme.eligibility.soft} />
                </ul>
              </>
            ) : null}
          </section>

          {scheme.matched_hard_conditions.length > 0 ? (
            <section>
              <h4>What your answers already meet</h4>
              <ul>
                {scheme.matched_hard_conditions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
          ) : null}

          {scheme.unknown_conditions.length > 0 ? (
            <section>
              <h4>Not checked yet — missing from your answers</h4>
              <ul>
                {scheme.unknown_conditions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
          ) : null}

          <section>
            <h4>Documents usually required</h4>
            <ul>
              {scheme.documents_required.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>

          <section>
            <h4>How to apply</h4>
            <p>{scheme.application_process}</p>
          </section>

          {scheme.verification_status !== "verified" ? (
            <p className="verify-note">
              These scheme details haven&rsquo;t been verified against the
              official source yet — treat them as a starting point.
            </p>
          ) : null}
        </div>
      </details>

      <div className="official">
        <p className="official-title">
          Verify &amp; apply on the official government site
        </p>
        <p className="official-copy">
          What you see here is only an estimate based on the details you entered.
          Confirm the current rules and submit your application on the official
          site.
        </p>
        <p className="official-links">
          <a
            href={scheme.official_source_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Official scheme page ↗
          </a>
          {scheme.apply_url ? (
            <a href={scheme.apply_url} target="_blank" rel="noopener noreferrer">
              Apply online ↗
            </a>
          ) : null}
        </p>
      </div>
    </article>
  );
}

interface ResultsListProps {
  results: MatchedScheme[];
  onRefine: () => void;
}

export function ResultsList({ results, onRefine }: ResultsListProps) {
  const likely = results.filter((r) => r.bucket === "likely_eligible");
  const possibly = results.filter((r) => r.bucket === "possibly_eligible");

  return (
    <div className="results">
      <button type="button" className="btn-link back" onClick={onRefine}>
        ← Refine search
      </button>

      {results.length === 0 ? (
        <div className="empty">
          <h2>No matches with the details provided</h2>
          <p>
            None of the schemes in this tool could be matched to what you
            entered. That usually means a few key details are missing rather than
            that nothing applies to you.
          </p>
          <p>
            Try adding your <strong>state</strong>,{" "}
            <strong>annual family income</strong>, <strong>category</strong>, or
            the <strong>kind of support</strong> you need, then search again.
          </p>
          <button type="button" className="btn-primary" onClick={onRefine}>
            Add more details
          </button>
        </div>
      ) : (
        <>
          <p className="disclaimer" role="note">
            These results are an automated estimate based only on what you
            entered — not a decision or a guarantee. Always confirm eligibility
            and apply on the official government website linked in each scheme.
          </p>

          {likely.length > 0 ? (
            <section className="bucket">
              <h2 className="bucket-head likely">
                Likely eligible <span>({likely.length})</span>
              </h2>
              <p className="bucket-sub">
                Your answers match every requirement we were able to check.
              </p>
              {likely.map((scheme) => (
                <SchemeCard key={scheme.scheme_id} scheme={scheme} />
              ))}
            </section>
          ) : null}

          {possibly.length > 0 ? (
            <section className="bucket">
              <h2 className="bucket-head possibly">
                Possibly eligible <span>({possibly.length})</span>
              </h2>
              <p className="bucket-sub">
                You meet part of the criteria; some details are still missing.
              </p>
              {possibly.map((scheme) => (
                <SchemeCard key={scheme.scheme_id} scheme={scheme} />
              ))}
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
