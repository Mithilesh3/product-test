import { type CSSProperties, type ReactNode } from "react";

type SectionTemplateType = "insight" | "grid" | "visual" | "summary" | "analysis";
type SectionVisualType = "none" | "icon" | "chart" | "matrix" | "illustration";

type SectionSummaryItem = {
  label: string;
  value: string;
};

type ReportTemplateThemeConfig = {
  backgroundTop: string;
  backgroundMid: string;
  backgroundBottom: string;
  primaryText: string;
  secondaryText: string;
  accentGold: string;
  cardBackground: string;
  cardBorder: string;
};

export type ReportSectionTemplateData = {
  sectionNumber: string;
  title: string;
  subtitle?: string;
  type?: SectionTemplateType;
  tag?: string;
  summaryItems?: SectionSummaryItem[];
  highlightValue?: string;
  bodyTitle?: string;
  bodyText?: string;
  notes?: string[];
  bullets?: string[];
  takeaways?: string[];
  visualType?: SectionVisualType;
  visualNode?: ReactNode;
  content?: ReactNode;
  pageClassName?: string;
};

const DEFAULT_THEME: ReportTemplateThemeConfig = {
  backgroundTop: "#FFF8E7",
  backgroundMid: "#FFF3C4",
  backgroundBottom: "#FFE9A8",
  primaryText: "#4A3419",
  secondaryText: "#7A5A2B",
  accentGold: "#D4A437",
  cardBackground: "rgba(255,255,255,0.72)",
  cardBorder: "rgba(212,164,55,0.35)",
};

function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

function toCssVars(theme: ReportTemplateThemeConfig) {
  return {
    "--rt-bg-top": theme.backgroundTop,
    "--rt-bg-mid": theme.backgroundMid,
    "--rt-bg-bottom": theme.backgroundBottom,
    "--rt-text-primary": theme.primaryText,
    "--rt-text-secondary": theme.secondaryText,
    "--rt-accent-gold": theme.accentGold,
    "--rt-card-bg": theme.cardBackground,
    "--rt-card-border": theme.cardBorder,
  } as CSSProperties;
}

export function ReportPageBackground({
  theme,
  className,
  children,
}: {
  theme: ReportTemplateThemeConfig;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cx("report-section-page report-template-page", className)} style={toCssVars(theme)}>
      <div className="report-template-watermark" aria-hidden="true" />
      {children}
    </div>
  );
}

export function SectionBadge({ number }: { number: string }) {
  return <div className="report-template-badge">{number}</div>;
}

export function SectionTagPill({ tag }: { tag: string }) {
  return <div className="report-template-tag">{tag}</div>;
}

export function SectionHeader({
  sectionNumber,
  title,
  subtitle,
  tag,
}: {
  sectionNumber: string;
  title: string;
  subtitle?: string;
  tag?: string;
}) {
  return (
    <header className="report-template-header">
      <div className="report-template-header__left">
        <SectionBadge number={sectionNumber} />
        <div className="report-template-header__copy">
          <h2 className="report-template-title">{title}</h2>
          {subtitle ? <p className="report-template-subtitle">{subtitle}</p> : null}
        </div>
      </div>
      {tag ? <SectionTagPill tag={tag} /> : null}
    </header>
  );
}

export function MainContentCard({ children }: { children: ReactNode }) {
  return <section className="report-template-card">{children}</section>;
}

export function KeyValueList({ items }: { items: SectionSummaryItem[] }) {
  if (!items.length) return null;
  return (
    <div className="report-template-kv">
      {items.map((item, idx) => (
        <div key={`${item.label}-${idx}`} className="report-template-kv__row">
          <p className="report-template-kv__label">{item.label}</p>
          <p className="report-template-kv__value">{item.value}</p>
        </div>
      ))}
    </div>
  );
}

export function HighlightValueBlock({ value }: { value: string }) {
  if (!value) return null;
  return <div className="report-template-highlight">{value}</div>;
}

export function InsightTextPanel({
  title,
  text,
  bullets,
}: {
  title?: string;
  text?: string;
  bullets?: string[];
}) {
  const safeBullets = (bullets || []).filter((item) => String(item || "").trim());
  return (
    <div className="report-template-insight">
      {title ? <h3 className="report-template-insight__title">{title}</h3> : null}
      {text ? <p className="report-template-insight__text">{text}</p> : null}
      {safeBullets.length ? (
        <ul className="report-template-insight__list">
          {safeBullets.map((item, idx) => (
            <li key={`${item}-${idx}`}>{item}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function NotesStrip({ notes }: { notes: string[] }) {
  const safeNotes = notes.filter((item) => String(item || "").trim());
  if (!safeNotes.length) return null;
  return (
    <div className="report-template-notes">
      {safeNotes.map((note, idx) => (
        <p key={`${note}-${idx}`}>{note}</p>
      ))}
    </div>
  );
}

export function TakeawayChips({ takeaways }: { takeaways: string[] }) {
  const safeTakeaways = takeaways.filter((item) => String(item || "").trim());
  if (!safeTakeaways.length) return null;
  return (
    <div className="report-template-takeaways">
      {safeTakeaways.map((takeaway, idx) => (
        <span key={`${takeaway}-${idx}`} className="report-template-chip">
          {takeaway}
        </span>
      ))}
    </div>
  );
}

export function VisualPlaceholder({ visualType }: { visualType: SectionVisualType }) {
  if (!visualType || visualType === "none") return null;
  return (
    <div className="report-template-visual" aria-label={`visual-${visualType}`}>
      <span>{visualType.toUpperCase()}</span>
    </div>
  );
}

export function GridCard({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return (
    <article className="report-template-grid-card">
      <h4>{title}</h4>
      <p>{body}</p>
    </article>
  );
}

export function FooterSummaryRibbon({ points }: { points: string[] }) {
  if (!points.length) return null;
  return (
    <footer className="report-template-ribbon">
      {points.map((point, idx) => (
        <span key={`${point}-${idx}`}>{point}</span>
      ))}
    </footer>
  );
}

function renderInsightLayout(sectionData: ReportSectionTemplateData) {
  return (
    <div className="report-template-layout report-template-layout--insight">
      <div className="report-template-col">
        <KeyValueList items={sectionData.summaryItems || []} />
        <HighlightValueBlock value={String(sectionData.highlightValue || "")} />
        <NotesStrip notes={sectionData.notes || []} />
      </div>
      <div className="report-template-col">
        <InsightTextPanel title={sectionData.bodyTitle} text={sectionData.bodyText} bullets={sectionData.bullets} />
        {sectionData.content ? <div className="report-template-slot">{sectionData.content}</div> : null}
      </div>
    </div>
  );
}

function renderGridLayout(sectionData: ReportSectionTemplateData) {
  const cards = (sectionData.bullets || []).slice(0, 6);
  return (
    <div className="report-template-layout report-template-layout--grid">
      <div className="report-template-grid">
        {cards.length
          ? cards.map((card, idx) => (
              <GridCard key={`${card}-${idx}`} title={`Point ${idx + 1}`} body={card} />
            ))
          : (sectionData.summaryItems || []).slice(0, 6).map((item, idx) => (
              <GridCard key={`${item.label}-${idx}`} title={item.label} body={item.value} />
            ))}
      </div>
      {sectionData.content ? <div className="report-template-slot">{sectionData.content}</div> : null}
    </div>
  );
}

function renderVisualLayout(sectionData: ReportSectionTemplateData) {
  return (
    <div className="report-template-layout report-template-layout--visual">
      <div className="report-template-col">
        {sectionData.visualNode || <VisualPlaceholder visualType={sectionData.visualType || "matrix"} />}
      </div>
      <div className="report-template-col">
        <InsightTextPanel title={sectionData.bodyTitle} text={sectionData.bodyText} bullets={sectionData.bullets} />
        <KeyValueList items={sectionData.summaryItems || []} />
        {sectionData.content ? <div className="report-template-slot">{sectionData.content}</div> : null}
      </div>
    </div>
  );
}

function renderSummaryLayout(sectionData: ReportSectionTemplateData) {
  return (
    <div className="report-template-layout report-template-layout--summary">
      <HighlightValueBlock value={String(sectionData.highlightValue || "")} />
      <InsightTextPanel title={sectionData.bodyTitle} text={sectionData.bodyText} bullets={sectionData.bullets} />
      <NotesStrip notes={sectionData.notes || []} />
      {sectionData.content ? <div className="report-template-slot">{sectionData.content}</div> : null}
    </div>
  );
}

function renderByType(sectionData: ReportSectionTemplateData) {
  switch (sectionData.type) {
    case "grid":
      return renderGridLayout(sectionData);
    case "visual":
      return renderVisualLayout(sectionData);
    case "summary":
      return renderSummaryLayout(sectionData);
    case "analysis":
      return renderInsightLayout(sectionData);
    case "insight":
    default:
      return renderInsightLayout(sectionData);
  }
}

export function renderSectionPage(
  sectionData: ReportSectionTemplateData,
  themeConfig?: Partial<ReportTemplateThemeConfig>,
) {
  const theme = { ...DEFAULT_THEME, ...(themeConfig || {}) };
  const safeTakeaways = (sectionData.takeaways || []).slice(0, 4);

  return (
    <ReportPageBackground theme={theme} className={sectionData.pageClassName}>
      <SectionHeader
        sectionNumber={sectionData.sectionNumber}
        title={sectionData.title}
        subtitle={sectionData.subtitle}
        tag={sectionData.tag}
      />
      <div className="report-section-body report-template-body">
        <MainContentCard>{renderByType(sectionData)}</MainContentCard>
      </div>
      <FooterSummaryRibbon points={safeTakeaways} />
    </ReportPageBackground>
  );
}

export type { ReportTemplateThemeConfig, SectionTemplateType, SectionVisualType, SectionSummaryItem };
