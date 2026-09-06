import {
  Hero, Stats, Finding, Inbound, Outbound, TrustLine, Modules, Regulatory, CTA,
} from '../components/Sections';
import NextPhase from '../components/NextPhase';

export default function Home() {
  return (
    <>
      <Hero />
      <Stats />
      <Finding />
      <Inbound />
      <Outbound />
      <TrustLine />
      <Modules />
      <NextPhase />
      <Regulatory />
      <CTA />
    </>
  );
}
