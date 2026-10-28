import { AnimatePresence, motion } from 'framer-motion';
import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  FileCheck2,
  FileSearch,
  FileText,
  LoaderCircle,
  ShieldCheck,
} from 'lucide-react';
import type { DocumentProgressStatus, DocumentReview, DocumentStreamEvent } from '../types';

const stageConfig = [
  { id: 'received', title: 'Document received', description: 'Your file has entered the claim review queue.' },
  { id: 'reading', title: 'Reading document', description: 'We are checking for readable text and source details.' },
  { id: 'extracting', title: 'Extracting important details', description: 'We are pulling out policy, billing, and treatment facts.' },
  { id: 'requirements', title: 'Checking insurer requirements', description: 'We are comparing the document against the rulebook.' },
  { id: 'claim_compare', title: 'Comparing with your claim', description: 'We are checking names, dates, and amounts against the claim record.' },
  { id: 'explanation', title: 'Preparing your explanation', description: 'We are writing the final summary and next steps.' },
] as const;

const statusStyles: Record<DocumentProgressStatus, string> = {
  pending: 'border-slate-700 bg-slate-900/50 text-slate-300',
  active: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200',
  completed: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200',
  failed: 'border-rose-500/40 bg-rose-500/10 text-rose-200',
};

const getStatusIcon = (status: DocumentProgressStatus) => {
  switch (status) {
    case 'completed':
      return CheckCircle2;
    case 'active':
      return LoaderCircle;
    case 'failed':
      return AlertTriangle;
    default:
      return CircleDashed;
  }
};

type Props = {
  filename?: string | null;
  documentType?: string | null;
  events: DocumentStreamEvent[];
  result?: DocumentReview | null;
  error?: string | null;
};

export function DocumentProgressPanel({ filename, documentType, events, result, error }: Props) {
  const stageStatusMap = new Map<string, DocumentProgressStatus>();
  const liveEvent = [...events].reverse().find((event) => event.stage && stageConfig.some((item) => item.id === event.stage));

  for (const event of events) {
    if (!event.stage) continue;
    stageStatusMap.set(event.stage, event.status ?? 'pending');
  }

  const stageRows = stageConfig.map((stage) => {
    const status = stageStatusMap.get(stage.id) ?? 'pending';
    const Icon = getStatusIcon(status);
    return {
      ...stage,
      status,
      Icon,
    };
  });

  const currentMessage = liveEvent?.details ?? liveEvent?.message ?? 'We are preparing the review.';
  const currentStatus = liveEvent?.status ?? 'pending';

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-950/40 p-5">
      <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Document review</p>
          <h3 className="mt-2 text-2xl font-bold text-white">What&apos;s happening with your document?</h3>
        </div>
        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-cyan-200">
          <ShieldCheck className="h-4 w-4" />
          {currentStatus === 'failed' ? 'Action needed' : 'Live status'}
        </div>
      </div>

      <div className="mb-5 flex flex-wrap gap-2 text-sm text-slate-300">
        {filename && (
          <span className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1.5">
            <FileText className="h-4 w-4 text-cyan-300" />
            {filename}
          </span>
        )}
        {documentType && (
          <span className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-cyan-200">
            <FileSearch className="h-4 w-4" />
            {documentType}
          </span>
        )}
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
        <div className="mb-3 flex items-center gap-3">
          <div className={`rounded-full p-2 ${statusStyles[currentStatus]}`}>
            {currentStatus === 'active' ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <FileCheck2 className="h-5 w-5" />}
          </div>
          <div>
            <div className="text-sm font-medium text-slate-100">{liveEvent?.message ?? 'Waiting for document analysis'}</div>
            <div className="text-sm text-slate-300">{currentMessage}</div>
          </div>
        </div>

        <div className="space-y-3">
          {stageRows.map((stage, index) => (
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.04 }}
              className={`flex items-start gap-3 rounded-2xl border p-3 ${statusStyles[stage.status]}`}
            >
              <div className="mt-0.5 rounded-full bg-slate-950/60 p-1">
                <stage.Icon className="h-4 w-4" />
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium">{stage.title}</div>
                <div className="text-xs opacity-80">{stage.description}</div>
              </div>
              <span className="rounded-full border border-current/20 px-2 py-1 text-[10px] uppercase tracking-[0.2em]">
                {stage.status}
              </span>
            </motion.div>
          ))}
        </div>
      </div>

      <AnimatePresence mode="wait">
        {error && (
          <motion.div
            key={error}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {result && (
        <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div className="text-lg font-semibold text-white">Validation result</div>
            <span className={`rounded-full px-2 py-1 text-xs ${result.valid ? 'bg-emerald-500/10 text-emerald-300' : 'bg-amber-500/10 text-amber-300'}`}>
              {result.valid ? 'Ready' : 'Needs attention'}
            </span>
          </div>
          <div className="mb-2 text-sm text-slate-300">Score: {result.score}/100</div>

          {result.missing_documents.length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Missing documents</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-200">
                {result.missing_documents.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          )}

          {result.mismatches.length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Mismatches</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-200">
                {result.mismatches.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          )}

          {result.next_steps.length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Recommended next steps</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-200">
                {result.next_steps.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
