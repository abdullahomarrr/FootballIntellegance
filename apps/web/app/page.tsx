import evidence from "./data/landing-evidence.json";
import coverage from "./data/landing-coverage.json";
import s from "./landing.module.css";

const number = (value: number | string, digits = 0) => new Intl.NumberFormat("en-GB", { maximumFractionDigits: digits }).format(Number(value));
const season = evidence.seasons.data[0];
const metrics = ["passes_per_90", "key_passes_per_90", "assists_per_90"].map(key => evidence.metrics.data.find(row => row.metric_name === key)!);
const labels = ["Passes per 90", "Key passes per 90", "Assists per 90"];
const arrow = <span aria-hidden="true">↗</span>;
const fixtureCount = coverage.openfootball.reduce((sum, row) => sum + row.fixture_count, 0);
const matchCount = coverage.statsbomb.reduce((sum, row) => sum + row.match_count, 0);

export default function Home() {
  return <main className={s.page} id="main-content">
    <section className={s.hero} aria-labelledby="landing-title">
      <div className={s.heroPhoto} aria-hidden="true" />
      <div className={s.heroContent}>
        <p className={s.label}>Football recruitment intelligence</p>
        <h1 id="landing-title">Build your next<br /><span>starting XI.</span></h1>
        <p className={s.heroCopy}>Browse every top-five-league squad, find similar players and upgrades, and compare them side by side.<br />Every number shows where it came from.</p>
        <div className={s.heroActions}><a className={s.primary} href="/players">Explore players {arrow}</a><a className={s.heroLink} href="#what-we-do">Discover the workspace <span aria-hidden="true">↓</span></a></div>
      </div>
      <div className={s.heroBottom}><span>Player discovery / Performance analysis / Recruitment</span><span>For the decisions that shape a team.</span></div>
    </section>

    <section className={s.overview} id="what-we-do" aria-labelledby="overview-title">
      <p className={s.label}>What we do</p>
      <div className={s.split}><h2 id="overview-title">Football knowledge.<br /><span>A stronger foundation.</span></h2><div className={s.bodyCopy}><p>Bring player performance, qualified comparisons, market context and recruitment decisions into one workspace.</p><p>Start with a name or a role. Explore the underlying evidence, understand the differences between players, and keep your reasoning attached to the shortlist.</p><a className={s.textLink} href="/recruitment">Find your next player {arrow}</a></div></div>
    </section>

    <section className={s.pillars} aria-labelledby="pillars-title">
      <p className={s.label}>One connected recruitment workspace</p>
      <h2 id="pillars-title">Three pillars.<br /><span>One decision trail.</span></h2>
      <div className={s.pillarGrid}>
        <a href="/players"><span>01</span><h3>Player Intelligence</h3><p>Explore position-specific event percentiles, goalkeeper analytics, heatmaps, expected-threat and pass maps, player archetypes, team tactical context and explainable scouting reports, plus current-season Premier League and La Liga stats.</p><b>Explore players {arrow}</b></a>
        <a href="/market"><span>02</span><h3>Market Intelligence</h3><p>Review market value history, transfers and contracts from a dated, licence-checked snapshot, and source-linked news whose quotes are checked against the original. All of it kept separate from football ability.</p><b>Review the market view {arrow}</b></a>
        <a href="/recruitment"><span>03</span><h3>Recruitment Planning</h3><p>Combine balanced style similarity with a transparent role brief, filter by maximum value, compare candidates side by side and plan the squad budget, with the evidence kept behind every shortlist decision.</p><b>Build a search {arrow}</b></a>
      </div>
    </section>

    <section className={s.coverage} id="coverage" aria-labelledby="coverage-title">
      <div className={s.sectionLabel}><h2 className={s.label} id="coverage-title">Inside the data</h2><a href="/coverage">Explore coverage {arrow}</a></div>
      <div className={s.coverageStats}>
        <div><strong>{coverage.openfootball.length}<span> leagues</span></strong><p>Current fixture coverage</p></div>
        <div><strong>{number(fixtureCount)}</strong><p>Fixtures · 2026/27 catalogue</p></div>
        <div><strong>{number(matchCount)}</strong><p>Historical StatsBomb matches</p></div>
        <div><strong>{coverage.statsbomb.length}</strong><p>StatsBomb competition-seasons</p></div>
      </div>
      <p className={s.sourceNote}>Coverage snapshot · {coverage.meta.data_as_of.slice(0,10)}. Current fixtures and historical event data are separate datasets. Event data comes from StatsBomb Open and Wyscout Open, including recent international tournaments, and the two providers are never merged.</p>
      <div className={s.leagues}>{coverage.openfootball.map(row => <span key={row.competition_code}>{row.competition_name}</span>)}</div>
    </section>

    <section className={s.investigation} id="investigation" aria-labelledby="investigation-title">
      <aside className={s.margin}><p className={s.label}>The player in context</p><figure className={s.portrait}><img src="/images/toni-kroos.jpg" alt="Toni Kroos playing for Real Madrid" width={500} height={766} /><figcaption>Photo: <a href="https://commons.wikimedia.org/wiki/File:Toni_Kroos_-_CdR_-_RM_v_ATL_(cropped).jpg">DSanchez17</a>, <a href="https://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>, cropped</figcaption></figure><div><p>Historical study</p><strong>Toni Kroos</strong><span>{season.team_name} · {season.season_label}</span></div><div><p>Evidence base</p><strong>{number(season.minutes_played)} minutes</strong><span>Wyscout Open · Midfield</span></div><a className={s.textLink} href={`/players/${evidence.player.data.player_id}`}>View full profile {arrow}</a></aside>
      <div className={s.story}><h2 id="investigation-title">A real observation layer.<br /><span>Then the football interpretation.</span></h2><p>This dated Kroos sample shows the verified baseline beneath the product. The live profile builds on it with advanced event families, spatial behaviour, archetype evidence, strengths and review questions—without pretending this historical season is current form. Current-season Premier League and La Liga players carry a separate stats tier, clearly labelled, with no event locations.</p><div className={s.rawStats}>{metrics.map((metric,i)=><div key={metric.metric_name}><strong>{number(metric.metric_value,2)}</strong><span>{labels[i]}</span><small>{number(metric.percentile,1)} percentile</small></div>)}</div><p className={s.sourceNote}>Spanish first division · {season.season_label} · Same position group · Minimum 900 minutes. This is a real captured baseline, not a current transfer recommendation.</p></div>
    </section>

    <section className={s.comparison} aria-labelledby="comparison-title">
      <p className={s.label}>The intelligence layer</p>
      <div className={s.split}><h2 id="comparison-title">From match events.<br /><span>To a defensible decision.</span></h2><div className={s.bodyCopy}><p>The system does not collapse a player into one mystery rating. It keeps style resemblance, role suitability, evidence coverage and human judgment visible as different parts of the decision.</p><p className={s.reference}>15 outfield metrics · 7 goalkeeper metrics · evidence retained at selection</p></div></div>
      <div className={s.comparisonRows}>
        <article className={s.candidate}><span className={s.rank}>01</span><div className={s.candidateIdentity}><h3>Context first</h3><p>Competition · season · broad position · qualified minutes</p></div><div className={s.candidateDetail}><span>Evidence population</span><strong>900+</strong><p>Small groups (under 15 players) are ranked in a wider same-provider position pool and labelled as such. Unavailable metrics stay missing.</p></div><div className={s.score}><strong>22</strong><span>advanced metrics</span></div></article>
        <article className={s.candidate}><span className={s.rank}>02</span><div className={s.candidateIdentity}><h3>Explain the alternatives</h3><p>Balanced style similarity remains separate from tactical preference.</p></div><div className={s.candidateDetail}><span>What the scout sees</span><strong>↔</strong><p>Feature overlap, closest evidence, largest trade-off, confidence and missing coverage.</p></div><div className={s.score}><strong>60%</strong><span>minimum feature overlap</span></div></article>
        <article className={s.candidate}><span className={s.rank}>03</span><div className={s.candidateIdentity}><h3>Preserve the reasoning</h3><p>A role brief changes fit—not the meaning of similarity.</p></div><div className={s.candidateDetail}><span>Decision trail</span><strong>✓</strong><p>Recommendation, role fit, reference context and model version are captured when shortlisted.</p></div><div className={s.score}><strong>60/40</strong><span>similarity / role fit</span></div></article>
      </div>
      <div className={s.comparisonFoot}><p>Scores narrow a review; they are not probabilities of success. Video, live observation, medical context and human judgment remain required.</p><a className={s.textLink} href="/recruitment">Open intelligent recruitment {arrow}</a></div>
    </section>

    <section className={s.methodology} id="methodology" aria-labelledby="methodology-title"><p className={s.label}>A clear view of the evidence</p><div className={s.split}><h2 id="methodology-title">Know the possibilities.<br /><span>Understand the limits.</span></h2><div className={s.methodList}><details><summary>Every season has a date <span aria-hidden="true">+</span></summary><p>The player study uses {season.season_label} observations, captured on {evidence.captured_at.slice(0,10)}. It demonstrates historical analysis, not a current transfer recommendation.</p></details><details><summary>Every comparison has a context <span aria-hidden="true">+</span></summary><p>Peers share a competition, season and broad provider position group, with a minimum of 900 minutes. When that group has fewer than 15 players, the ranking uses a wider same-provider position pool and the page says so. Matching position groups does not guarantee identical tactical roles.</p></details><details><summary>Missing data stays missing <span aria-hidden="true">+</span></summary><p>Event data does not establish physical tracking, injuries or current availability. Market values come from a separate, dated snapshot, and news claims are quoted from their source and labelled unverified. Unavailable observations stay unavailable.</p></details><a className={s.textLink} href="/coverage">Read the coverage notes {arrow}</a></div></div></section>

    <footer className={s.footer}>
      <div className={s.footerTop}><div><p className={s.label}>Your next recruitment decision</p><h2>Start with the player.</h2></div><a className={s.primary} href="/players">Open the workspace {arrow}</a></div>
      <div className={s.footerGrid}><a className={s.footerBrand} href="/">Football<br />Intelligence<span>Built for the work behind the signing.</span></a><div><p>Workspace</p><a href="/players">Player directory</a><a href="/recruitment">Recruitment search</a><a href="/analysis">Compare players</a><a href="/shortlists">Shortlists &amp; budget</a><a href="/market">Market</a></div><div><p>The evidence</p><a href="/coverage">Data coverage</a><a href="#methodology">Our approach</a><a href="#investigation">Player study</a></div></div>
      <div className={s.footerBottom}><span>Football Intelligence · Human judgement, always.</span><a href="https://commons.wikimedia.org/wiki/File:Well_lit_soccer_stadium_(Unsplash).jpg">Photography: Mario Klassen / CC0</a></div>
    </footer>
  </main>;
}
