import { useEffect, useRef, useState } from 'react';
import Reveal from './Reveal';
import {
  OfficerReviewing,
  ModelsDisagree,
  ScamCall,
  DocsCleared,
  ModuleIcon,
  Tick,
} from '../illustrations/Illustrations';
import * as C from '../data/content';

/* ----------------------------------------------------------------- hero */

export function Hero() {
  return (
    <section className="hero">
      <div className="wrap hero-grid">
        <div>
          <span className="eyebrow">{C.hero.eyebrow}</span>
          <h1>
            Every fake has a tell.
            <br />
            We read it <span className="mark draw">before</span>
            <br />
            the loan does.
          </h1>
          <p className="hero-sub">
            Litmus checks both directions of a loan relationship — that the person applying is a
            real human, and that the call telling them they’re approved is really from you.{' '}
            <b>
              We benchmarked our own detectors before building anything, and we publish what they
              got wrong.
            </b>
          </p>
          <div className="hero-actions">
            <a className="btn btn-primary" href="#finding">
              See what we measured <span className="arw">→</span>
            </a>
            <a className="btn btn-ghost" href="#modules">
              Read the architecture
            </a>
          </div>
          <div className="hero-meta">
            {C.hero.chips.map((chip) => (
              <span className="chip" key={chip.value}>
                {chip.pip && <span className="pip" />}
                <b>{chip.value}</b> {chip.text}
              </span>
            ))}
          </div>
        </div>

        <div className="hero-art">
          <div className="verdict v-a">
            <span className="dotv" />
            MODEL 1 · FAKE 88.9%
          </div>
          <div className="verdict v-b">
            <span className="dotv" />
            MODEL 2 · REAL 99.9%
          </div>
          <OfficerReviewing />
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- stats */

export function Stats() {
  return (
    <section className="alt stats-band">
      <div className="wrap">
        <div className="stat-grid">
          {C.stats.map((stat, i) => (
            <StatCard key={stat.value} stat={stat} delay={i * 0.075} />
          ))}
        </div>
      </div>
    </section>
  );
}

function StatCard({ stat, delay }) {
  const ref = useRef(null);
  const [filled, setFilled] = useState(false);

  // The progress bar fills once the card is on screen. Purely decorative —
  // the figure itself is always rendered, never counted up from zero.
  useEffect(() => {
    const node = ref.current;
    if (!node || !('IntersectionObserver' in window)) return setFilled(true);
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setFilled(true)),
      { threshold: 0.4 },
    );
    io.observe(node);
    return () => io.disconnect();
  }, []);

  return (
    <Reveal className={`stat ${stat.tone} ${filled ? 'on' : ''}`} delay={delay}>
      <div ref={ref}>
        <div className="snum">{stat.value}</div>
        <div className="slab">{stat.label}</div>
      </div>
      <div className="bar">
        <i />
      </div>
    </Reveal>
  );
}

/* -------------------------------------------------------------- finding */

export function Finding() {
  return (
    <section id="finding">
      <div className="wrap">
        <Reveal className="section-head">
          <span className="eyebrow">Start here</span>
          <h2>We tested four detection models before building anything else.</h2>
          <p>
            Every vendor in this category leads with an accuracy number. We led with a benchmark —
            because the number only means something once you know where it breaks.
          </p>
        </Reveal>

        <div className="tri">
          {C.finding.cards.map((card, i) => (
            <Reveal key={card.value} className={`tcard ${card.tone}`} delay={i * 0.075}>
              <div className="tn">{card.value}</div>
              <div className="tt">{card.title}</div>
              <div className="td">{card.note}</div>
            </Reveal>
          ))}
        </div>

        <Reveal className="verdict-box">
          <h3>The conclusion this product is built around</h3>
          {C.finding.verdict.map((line) => (
            <p key={line.slice(0, 24)}>{line}</p>
          ))}
          <div className="cite">{C.finding.cite}</div>
        </Reveal>
      </div>
    </section>
  );
}

/* ------------------------------------------------------ inbound/outbound */

function PointList({ points }) {
  return (
    <div className="list">
      {points.map((point) => (
        <div className="list-item" key={point.bold}>
          <Tick />
          <span>
            <b>{point.bold}</b> {point.text}
          </span>
        </div>
      ))}
    </div>
  );
}

export function Inbound() {
  return (
    <section className="alt" id="inbound">
      <div className="wrap split">
        <Reveal>
          <span className="eyebrow">{C.inbound.eyebrow}</span>
          <h3 className="split-title">{C.inbound.heading}</h3>
          <p className="lead">{C.inbound.lead}</p>
          <PointList points={C.inbound.points} />
        </Reveal>
        <Reveal className="art-col">
          <ModelsDisagree />
        </Reveal>
      </div>
    </section>
  );
}

export function Outbound() {
  return (
    <section id="outbound">
      <div className="wrap split flip">
        <Reveal className="art-col">
          <ScamCall />
        </Reveal>
        <Reveal>
          <span className="eyebrow">{C.outbound.eyebrow}</span>
          <h3 className="split-title">{C.outbound.heading}</h3>
          <p className="lead">{C.outbound.lead}</p>
          <PointList points={C.outbound.points} />
        </Reveal>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------ trustline */

export function TrustLine() {
  const { before, after, code, codeMeta, codeNote } = C.trustline;
  const reduced =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  return (
    <section className="alt">
      <div className="wrap">
        <Reveal className="section-head center">
          <span className="eyebrow">TrustLine</span>
          <h2>The arrow points the other way.</h2>
          <p>One protocol change removes the question a customer can never answer under pressure.</p>
        </Reveal>

        <Reveal className="flow">
          <FlowSide side="a" data={before} />
          <div className="farrow">VS</div>
          <FlowSide side="b" data={after} />
        </Reveal>

        <Reveal className="code-demo">
          <div className="clab">{codeMeta}</div>
          <div className="ccode">
            {reduced
              ? code
              : code.split('').map((ch, i) => (
                  <span key={`${ch}-${i}`} style={{ animationDelay: `${0.3 + i * 0.045}s` }}>
                    {ch}
                  </span>
                ))}
          </div>
          <div className="cnote">{codeNote}</div>
        </Reveal>
      </div>
    </section>
  );
}

function FlowSide({ side, data }) {
  const [from, verb, to] = data.flow;
  return (
    <div className={`fside ${side}`}>
      <div className="ftag">{data.tag}</div>
      <div className="fline">
        {from} <span className="ar">→</span> {verb} <span className="ar">→</span> {to}
      </div>
      <p>{data.note}</p>
    </div>
  );
}

/* -------------------------------------------------------------- modules */

export function Modules() {
  return (
    <section id="modules">
      <div className="wrap">
        <Reveal className="section-head">
          <span className="eyebrow">Architecture</span>
          <h2>Six modules. We tell you which three actually run.</h2>
          <p>
            Two shallow demos of six half-built things convince nobody. Three that work in front of
            you do — so the rest stay labelled as exactly what they are.
          </p>
        </Reveal>

        <div className="mods">
          {C.modules.map((mod, i) => (
            <Reveal key={mod.name} className="mcard" delay={i * 0.075}>
              <ModuleIcon name={mod.icon} />
              <div className="mrow">
                <h4>{mod.name}</h4>
                <span className={`tag ${mod.status}`}>
                  {mod.status === 'live' ? 'Built · Live' : 'Architecture'}
                </span>
              </div>
              <p>{mod.body}</p>
              <div className="mfoot">Answers: {mod.answers}</div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ----------------------------------------------------------- regulatory */

export function Regulatory() {
  return (
    <section className="alt" id="rules">
      <div className="wrap">
        <Reveal className="section-head">
          <span className="eyebrow">Regulatory fit</span>
          <h2>Built against instruments that already exist.</h2>
          <p>
            Not positioned ahead of regulation — mapped directly onto the three live Indian
            instruments that govern this exact problem.
          </p>
        </Reveal>
        <div className="regs">
          {C.regulations.map((reg, i) => (
            <Reveal key={reg.name} className="reg" delay={i * 0.075}>
              <div className="rn">{reg.name}</div>
              <div className="rw">{reg.when}</div>
              <p>{reg.body}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ cta */

export function CTA() {
  return (
    <section className="cta" id="cta">
      <div className="wrap">
        <Reveal className="cta-art">
          <DocsCleared />
        </Reveal>
        <h2>Read your pipeline’s actual trust score.</h2>
        <p>
          Three modules, one working API, tested against the failure modes we found ourselves — not
          the ones a vendor chose to show you.
        </p>
        <div className="hero-actions">
          <a className="btn btn-primary" href="#finding">
            See what we measured <span className="arw">→</span>
          </a>
          <a className="btn btn-ghost" href="#modules">
            Review the architecture
          </a>
        </div>
      </div>
    </section>
  );
}

