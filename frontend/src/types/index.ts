export type Claim = {
  id: string;
  customer_name: string;
  policy_number: string;
  product: string;
  claim_type: string;
  status: string;
  claim_amount: number;
  insurer: string;
  branch: string;
  summary: string;
  history?: { date: string; event: string }[];
  analysis?: {
    readiness_score: number;
    status: string;
    checklist: string[];
    next_steps: string[];
    deductible: number;
    copay: number;
    estimated_payout: number;
    risk_flags: string[];
  };
};

export type QueryResponse = {
  claim_id: string;
  answer: string;
  citations: string[];
  language: string;
  next_actions: string[];
  confidence: number;
  provider?: 'groq' | 'gemini' | 'deterministic' | 'replay';
};

export type RuleBook = {
  id: string;
  title: string;
  category: string;
  source: string;
  summary: string;
  keywords: string[];
  required_documents?: string[];
  required_fields?: string[];
  itemization_required?: boolean;
  signature_required?: boolean;
};

export type DocumentReview = {
  filename: string;
  valid: boolean;
  score: number | null;
  missing_documents: string[];
  mismatches: string[];
  next_steps: string[];
  fields_missing: string[];
  fields_unverified: string[];
  provider_message?: string | null;
  claim_id?: string | null;
  extraction_status?: 'extracted' | 'unreadable' | 'unsupported';
  extraction_message?: string | null;
  extracted_fields?: Record<string, string>;
  extracted_document_type?: string | null;
  checks_passed?: string[];
  readiness_score?: number | null;
  replayed?: boolean;
  provider?: 'groq' | 'deterministic' | 'replay';
};

export type DocumentProgressStatus = 'pending' | 'active' | 'completed' | 'failed';

export type DocumentStreamEvent = {
  type: string;
  stage: string;
  status?: DocumentProgressStatus;
  message: string;
  details?: string;
  progress?: number;
  claim_id?: string | null;
  session_id?: string | null;
  timestamp?: string;
  filename?: string;
  document_type?: string;
  error?: string;
  event_id?: string;
  result?: DocumentReview;
};

export const isTerminalDocumentEvent = (event: DocumentStreamEvent) =>
  event.type === 'document.completed' || event.type === 'document.failed';

export type ProviderStatus = {
  provider: string;
  state: 'configured' | 'not_configured' | 'replay';
  model: string | null;
  last_error: string | null;
  credentials_configured: boolean;
};
