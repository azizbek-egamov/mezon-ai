/** Ish tahlili hisoboti (GET /cases/{id}/report) va tasdiq oynasi (GET /cases/{id}/confirmation) tiplari.
 * Manba: mezon_backend/apps/cases/pipeline.py va export.confirmation_info. */

export interface Fact {
  id: string;
  type: string;
  page: number;
  date: string;
  time: string;
  source: string;
  summary: string;
  quote: string;
  verified: boolean;
  verified_page?: number | null;
}

export interface LegalSource {
  key: string;
  doc_title: string;
  label: string;
  lex_url: string;
}

export interface LegalAssessment {
  verdict?: "qonun_buzilishi" | "buzilish_ehtimoli" | "huquqiy_ahamiyatli" | "asossiz" | string;
  assessment?: string;
  correction_needed?: boolean;
  corrections?: string;
  defense_action?: string;
  verification?: { ok: boolean; issues: { severity: string; detail: string }[] };
  sources?: LegalSource[];
  error?: string;
  skipped?: boolean;
  model?: string;
  retried?: boolean;
}

export interface Finding {
  kind: "contradiction" | "procedural" | string;
  topic: string;
  fact_ids: string[];
  pages: number[];
  explanation: string;
  importance: "high" | "medium" | "low" | string;
  legal?: LegalAssessment;
}

export interface OcrPage {
  page: number;
  low_quality?: boolean;
  warning?: string;
  source?: string;
  has_handwriting?: boolean;
  stamps?: string[];
  cost_usd?: number;
}

export interface CaseReport {
  pages: number;
  summary: string;
  facts: Fact[];
  findings: Finding[];
  timeline: string[];
  pii_counts?: Record<string, number>;
  errors?: string[];
  ocr_pages?: OcrPage[];
  cost_usd?: number;
  seconds?: number;
}

export interface ConfirmationArticle {
  doc_title: string;
  label: string;
  lex_url: string;
  edition: string;
  /** "kuchda" | "kuchini yoʻqotgan" | "kuchga kirmagan" | "nomaʼlum" (o'zbekcha kalit, interfeysda tarjima qilinadi) */
  status: string;
  in_force: boolean;
}

export interface Confirmation {
  articles: ConfirmationArticle[];
  unverified: { topic: string; reason: string }[];
  confirmed_at: string | null;
}
