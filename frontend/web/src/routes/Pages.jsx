import Reveal from '../components/Reveal';
import * as Co from '../data/company';
import { apiGroups, modelCard, changelog } from '../data/engineering';

/**
 * The non-home marketing routes.
 *
 * Grouped in one module because they share a single layout vocabulary and none
 * is large on its own — splitting them into six files would add navigation cost
 * without adding structure.
 */

function PageHead({ eyebrow, title, lead }) {
  return (
    <div className="page-head">
      <div className="wrap">
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        {lead && <p>{lead}</p>}
      </div>
    </div>
  );
}

/* --------------------------------------------------------------- pricing */

export function Pricing() {
  return (
    <>
      <PageHead
        eyebrow="Pricing"
        title="Priced on exposure, not on headcount."
        lead="Fraud risk scales with how many verifications you run, so that is what you pay for."
      />
      <section>
        <div className="wrap">
          <div className="notice notice-warn wide">
            <b>Indicative.</b> {Co.pricing.note}
          </div>

          <div className="plan-grid">
            {Co.pricing.plans.map((plan, i) => (
              <Reveal
                key={plan.name}
                className={`plan ${plan.featured ? 'plan-featured' : ''}`}
                delay={i * 0.08}
              >
                {plan.featured && <div className="plan-flag">Most lenders start here</div>}
                <div className="plan-name">{plan.name}</div>
                <div className="plan-price">
                  {plan.price} <span className="plan-period">{plan.period}</span>
                </div>
                <p className="plan-tagline">{plan.tagline}</p>
                <ul className="plan-features">
                  {plan.features.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
                <a className={`btn ${plan.featured ? 'btn-primary' : 'btn-ghost'}`} href="#/company">
                  {plan.cta}
                </a>
              </Reveal>
            ))}
          </div>

          <div className="faq">
            <h2>Questions we get asked</h2>
            {Co.pricing.faq.map((item) => (
              <Reveal className="faq-item" key={item.q}>
                <div className="faq-q">{item.q}</div>
                <p className="faq-a">{item.a}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

/* ------------------------------------------------------------------ docs */

export function Docs() {
  return (
    <>
      <PageHead
        eyebrow="Documentation"
        title="API reference"
        lead="Every endpoint returns its own confidence and its own caveats. Nothing is a bare boolean."
      />
      <section>
        <div className="wrap">
          <div className="notice notice-info wide">
            <b>Base URL.</b> <code>http://127.0.0.1:8000</code> in development. All responses are
            JSON. Scoring endpoints take <code>multipart/form-data</code>; everything else takes
            JSON.
          </div>

          {apiGroups.map((group) => (
            <Reveal className="doc-group" key={group.group}>
              <h2>{group.group}</h2>
              <p className="doc-blurb">{group.blurb}</p>
              {group.endpoints.map((ep) => (
                <div className="endpoint" key={ep.path}>
                  <div className="ep-head">
                    <span className={`method method-${ep.method.toLowerCase()}`}>{ep.method}</span>
                    <code className="ep-path">{ep.path}</code>
                  </div>
                  <p className="ep-summary">{ep.summary}</p>
                  <div className="ep-grid">
                    <div>
                      <span className="ep-label">Request</span>
                      <code>{ep.body}</code>
                    </div>
                    <div>
                      <span className="ep-label">Returns</span>
                      <code>{ep.returns}</code>
                    </div>
                  </div>
                </div>
              ))}
            </Reveal>
          ))}

          <Reveal className="doc-group">
            <h2>Architecture</h2>
            <p className="doc-blurb">How a verification actually flows through the system.</p>
            <div className="arch-flow">
              {[
                { n: '1', t: 'Capture', d: 'A V-CIP frame or call audio arrives from the dealer point.' },
                { n: '2', t: 'Two models', d: 'Each modality is scored by two independent, differently-biased checkpoints.' },
                { n: '3', t: 'Fusion', d: 'Agreement plus confidence clears; disagreement routes to a person.' },
                { n: '4', t: 'Band', d: 'The routing band resolves from verdict states, never from score arithmetic.' },
                { n: '5', t: 'Intelligence', d: 'Outbound failures enrich with DoT FRI and publish to the consortium.' },
              ].map((step) => (
                <div className="arch-step" key={step.n}>
                  <div className="arch-n">{step.n}</div>
                  <div className="arch-t">{step.t}</div>
                  <div className="arch-d">{step.d}</div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}

/* -------------------------------------------------------------- security */

export function Security() {
  return (
    <>
      <PageHead
        eyebrow="Security & model card"
        title="What our models get wrong, and who they get wrong."
        lead="Published in full rather than summarised. This is the artifact a regulator asks for."
      />
      <section>
        <div className="wrap">
          <div className="notice notice-info wide">
            <b>Updated {modelCard.updated}.</b> {modelCard.intro}
          </div>

          <Reveal className="doc-group">
            <h2>Models in use</h2>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Module</th>
                    <th>Slot</th>
                    <th>Checkpoint</th>
                    <th>Benchmark</th>
                    <th>Note</th>
                  </tr>
                </thead>
                <tbody>
                  {modelCard.models.map((m) => (
                    <tr key={`${m.module}-${m.slot}`}>
                      <td>
                        <b>{m.module}</b>
                      </td>
                      <td className="mono">{m.slot}</td>
                      <td className="mono small">{m.id}</td>
                      <td className="mono">{m.benchmark}</td>
                      <td className="small">{m.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>

          <Reveal className="doc-group">
            <h2>Measured bias</h2>
            {modelCard.biases.map((b) => (
              <div className="bias-card" key={b.axis}>
                <div className="bias-axis">{b.axis}</div>
                <div className="bias-row">
                  <span className="bias-label">Finding</span>
                  <p>{b.finding}</p>
                </div>
                <div className="bias-row">
                  <span className="bias-label">Impact</span>
                  <p>{b.impact}</p>
                </div>
                <div className="bias-row">
                  <span className="bias-label">Mitigation</span>
                  <p>{b.mitigation}</p>
                </div>
              </div>
            ))}
          </Reveal>

          <Reveal className="doc-group">
            <h2>{modelCard.accuracy.heading}</h2>
            <p className="doc-blurb">{modelCard.accuracy.intro}</p>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr><th>Measure</th><th>Value</th><th>Reading</th></tr>
                </thead>
                <tbody>
                  {modelCard.accuracy.rows.map(([k, v, note]) => (
                    <tr key={k}>
                      <td><b>{k}</b></td>
                      <td className="mono">{v}</td>
                      <td className="small">{note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="notice notice-info">
              <b>Asymmetric gates.</b> {modelCard.accuracy.gates}
            </div>
          </Reveal>

          <Reveal className="doc-group">
            <h2>{modelCard.confound.heading}</h2>
            <div className="bias-card">
              <div className="bias-row">
                <span className="bias-label">What we saw</span>
                <p>{modelCard.confound.body}</p>
              </div>
              <div className="bias-row">
                <span className="bias-label">What we did</span>
                <p>{modelCard.confound.consequence}</p>
              </div>
              <div className="bias-row">
                <span className="bias-label">In production</span>
                <p>{modelCard.confound.why}</p>
              </div>
            </div>
          </Reveal>

          <Reveal className="doc-group">
            <h2>{modelCard.scopeCorrection.heading}</h2>
            <div className="notice notice-warn">{modelCard.scopeCorrection.body}</div>
          </Reveal>

          <Reveal className="doc-group">
            <h2>Known limits</h2>
            <ul className="limit-list">
              {modelCard.limits.map((l) => (
                <li key={l.slice(0, 30)}>{l}</li>
              ))}
            </ul>
          </Reveal>

          <Reveal className="doc-group">
            <h2>How TrustLine protects data</h2>
            <div className="principle-grid">
              {Co.principles.map((p) => (
                <div className="principle" key={p.title}>
                  <div className="principle-t">{p.title}</div>
                  <p>{p.body}</p>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}

/* --------------------------------------------------------------- company */

export function Company() {
  return (
    <>
      <PageHead
        eyebrow="Company"
        title="Litmus is early, and the site says so."
        lead="A pre-pilot product with three working modules and a published record of what they cannot do."
      />

      <section>
        <div className="wrap">
          <h2 className="sec-h2">{Co.market.headline}</h2>
          <div className="market-grid">
            {Co.market.cards.map((c, i) => (
              <Reveal className="market-card" key={c.value} delay={i * 0.07}>
                <div className="market-v">{c.value}</div>
                <div className="market-l">{c.label}</div>
                <p className="market-n">{c.note}</p>
                <div className="market-s">{c.source}</div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="alt">
        <div className="wrap narrow">
          <h2 className="sec-h2">{Co.wedge.heading}</h2>
          {Co.wedge.body.map((para) => (
            <p className="prose" key={para.slice(0, 24)}>
              {para}
            </p>
          ))}
        </div>
      </section>

      <section>
        <div className="wrap">
          <h2 className="sec-h2">Roadmap</h2>
          <div className="road-grid">
            {Co.roadmap.map((phase, i) => (
              <Reveal className={`road road-${phase.status}`} key={phase.phase} delay={i * 0.08}>
                <div className="road-head">
                  <span className="road-phase">{phase.phase}</span>
                  <span className="road-when">{phase.when}</span>
                </div>
                <ul>
                  {phase.items.map((item) => (
                    <li key={item.slice(0, 30)}>{item}</li>
                  ))}
                </ul>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="alt">
        <div className="wrap narrow">
          <h2 className="sec-h2">Team</h2>
          <p className="prose muted">{Co.team.note}</p>
          {Co.team.people.map((p) => (
            <div className="person" key={p.name}>
              <div className="person-name">{p.name}</div>
              <div className="person-role">{p.role}</div>
              <p className="person-detail">{p.detail}</p>
            </div>
          ))}
          <h3 className="hiring-h">Looking for</h3>
          <ul className="limit-list">
            {Co.team.hiring.map((h) => (
              <li key={h}>{h}</li>
            ))}
          </ul>
        </div>
      </section>
    </>
  );
}

/* ------------------------------------------------------------- changelog */

export function Changelog() {
  return (
    <>
      <PageHead
        eyebrow="Changelog"
        title="What changed, including what we broke."
        lead="Fixes are listed with the same weight as features. A bug we shipped is information a buyer deserves."
      />
      <section>
        <div className="wrap narrow">
          {changelog.map((release) => (
            <Reveal className="release" key={release.version}>
              <div className="release-head">
                <span className="release-v">v{release.version}</span>
                <span className="release-d">{release.date}</span>
                {release.tag && <span className="release-tag">{release.tag}</span>}
              </div>
              <ul className="release-list">
                {release.changes.map((c) => (
                  <li key={c.text.slice(0, 30)}>
                    <span className={`ctype ctype-${c.type}`}>{c.type}</span>
                    <span>{c.text}</span>
                  </li>
                ))}
              </ul>
            </Reveal>
          ))}
        </div>
      </section>
    </>
  );
}
