import { useState } from 'react';
import Reveal from './Reveal';
import { thesis, phase2, symmetry } from '../data/nextphase';

/**
 * Phase 2 section.
 *
 * Presented as a selectable list rather than four parallel cards, because the
 * items differ enormously in maturity — one is a designed protocol, two are
 * architecture only. Flattening them into identical cards would imply a
 * uniformity that does not exist, so each carries its own status line.
 */
export default function NextPhase() {
  const [active, setActive] = useState(phase2[0].id);
  const item = phase2.find((p) => p.id === active) ?? phase2[0];

  return (
    <section className="alt" id="next">
      <div className="wrap">
        <Reveal className="section-head">
          <span className="eyebrow">{thesis.eyebrow}</span>
          <h2>{thesis.heading}</h2>
          <p>{thesis.body}</p>
        </Reveal>

        <Reveal className="np-shell">
          <div className="np-list" role="tablist">
            {phase2.map((p) => (
              <button
                key={p.id}
                role="tab"
                aria-selected={p.id === active}
                className={`np-item ${p.id === active ? 'on' : ''}`}
                onClick={() => setActive(p.id)}
              >
                <span className="np-tag">{p.tag}</span>
                <span className="np-name">{p.name}</span>
                <span className="np-line">{p.line}</span>
              </button>
            ))}
          </div>

          <div className="np-detail" key={item.id}>
            <div className="np-detail-head">
              <h3>{item.name}</h3>
              <span className={`np-status ${item.built ? "np-built" : ""}`}>{item.status}</span>
            </div>

            <div className="np-block">
              <span className="np-label">The problem</span>
              <p>{item.problem}</p>
            </div>

            <div className="np-block">
              <span className="np-label">The idea</span>
              <p>{item.idea}</p>
            </div>

            <div className="np-block">
              <span className="np-label">Why it works</span>
              <ul className="np-why">
                {item.why.map((w) => (
                  <li key={w.slice(0, 28)}>{w}</li>
                ))}
              </ul>
            </div>

            {item.evidence && (
              <div className="np-block">
                <span className="np-label">Measured</span>
                <div className="np-evidence">
                  {item.evidence.map(([k, v]) => (
                    <div className="np-ev-row" key={k}>
                      <span className="np-ev-k">{k}</span>
                      <span className="np-ev-v">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="np-source">{item.source}</div>
          </div>
        </Reveal>

        <Reveal className="np-symmetry">
          <h3>{symmetry.heading}</h3>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Direction</th>
                  <th>Today</th>
                  <th>Phase 2</th>
                  <th>Shift</th>
                </tr>
              </thead>
              <tbody>
                {symmetry.rows.map((r) => (
                  <tr key={r.direction}>
                    <td><b>{r.direction}</b></td>
                    <td className="small">{r.today}</td>
                    <td className="small">{r.next}</td>
                    <td className="mono small np-shift">{r.shift}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
