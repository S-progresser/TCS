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
};

export type RuleBook = {
  id: string;
  title: string;
  category: string;
  source: string;
  summary: string;
  keywords: string[];
};

export type DocumentReview = {
  filename: string;
  valid: boolean;
  score: number;
  missing_documents: string[];
  mismatches: string[];
  next_steps: string[];
};

export type DocumentProgressStatus = 'pending' | 'active' | 'completed' | 'failed';

export type DocumentStreamEvent = {
  type: string;
  stage: string;
  status: DocumentProgressStatus;
  message: string;
  details?: string;
  progress?: number;
  claim_id?: string | null;
  session_id?: string | null;
  timestamp?: string;
  filename?: string;
  document_type?: string;
  error?: string;
  result?: DocumentReview;
};
