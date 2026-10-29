import { useMemo, useState } from 'react';
import { AlertCircle, Check, Circle, Clipboard, FileSearch, LoaderCircle } from 'lucide-react';
import type { DocumentProgressStatus, DocumentReview, DocumentStreamEvent } from '../types';

const stages = [
  { id: 'received', label: 'Document received' },
  { id: 'reading', label: 'Reading document' },
  { id: 'extracting', label: 'Extracting important details' },
  { id: 'requirements', label: 'Checking insurer requirements' },
  { id: 'claim_compare', label: 'Comparing with your claim' },
  { id: 'explanation', label: 'Preparing your explanation' },
] as const;

const statusClass: Record<DocumentProgressStatus, string> = {
  pending: 'stage-pending',
  active: 'stage-active',
  completed: 'stage-completed',
  failed: 'stage-failed',
};

type Props = {
  filename?: string | null;
  documentType?: string | null;
  events: DocumentStreamEvent[];
  result?: DocumentReview | null;
  error?: string | null;
  processing?: boolean;
  replayMode?: boolean;
};

export function DocumentProgressPanel({
  filename,
  documentType,
  events,
  result,
  error,
  processing = false,
  replayMode = false,
}: Props) {
  const [copied, setCopied] = useState(false);
  const { rows, latest, completedCount, complete, failed } = useMemo(() => {
    const statusByStage = new Map<string, DocumentProgressStatus>();
    for (const event of events) {
      if (!event.stage || !event.status || !stages.some((stage) => stage.id === event.stage)) continue;
      const previous = statusByStage.get(event.stage);
      if (previous === 'completed' && event.status !== 'failed') continue;
      statusByStage.set(event.stage, event.status);
    }
    const terminalSuccess = events.some((event) => event.type === 'document.completed');
    const rows = stages.map((stage) => ({
      ...stage,
      status: terminalSuccess ? 'completed' : statusByStage.get(stage.id) ?? 'pending',
    }));
    const latest = [...events].reverse().find((event) => event.message);
    const completedCount = rows.filter((stage) => stage.status === 'completed').length;
    const failed = rows.some((stage) => stage.status === 'failed');
    return { rows, latest, completedCount, complete: terminalSuccess || completedCount === stages.length, failed };
  }, [events]);

  const copyProviderMessage = async () => {
    if (!result?.provider_message) return;
    await navigator.clipboard.writeText(result.provider_message);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  const currentStatus = failed ? 'Action needed' : complete ? 'Review complete' : processing ? 'Analysis in progress' : 'Ready when you are';

  return (
    <section className="surface-card p-4 sm:p-5" aria-labelledby="document-progress-title" aria-live="polite">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="eyebrow">Document workspace</p>
          <h2 id="document-progress-title" className="mt-1 text-lg font-semibold text-slate-950">
            What&apos;s happening with your document?
          </h2>
        </div>
        <span className={`status-pill ${failed ? 'status-danger' : complete ? 'status-good' : 'status-neutral'}`}>
          {processing && !failed ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <FileSearch className="h-3.5 w-3.5" />}
          {replayMode || result?.replayed ? 'Replay · simulated' : currentStatus}
        </span>
      </div>

      {(filename || documentType) && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          {filename && <span className="file-chip">{filename}</span>}
          {documentType && <span className="file-chip file-chip-accent">{documentType}</span>}
        </div>
      )}

      <div className="mt-4 rounded-xl bg-slate-50 px-3 py-3">
        <div className="flex items-start gap-2.5">
          {failed ? <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" /> : processing ? <LoaderCircle className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-teal-700" /> : <FileSearch className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" />}
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-900">{latest?.message ?? 'Choose a file to begin a review'}</p>
            <p className="mt-0.5 text-xs leading-5 text-slate-600">
              {latest?.details ?? 'We check the uploaded content against the selected claim and its demo rulebook.'}
            </p>
            {processing && (
              <p className="mt-1 text-xs font-medium text-teal-800">
                {completedCount} of {stages.length} stages confirmed
              </p>
            )}
          </div>
        </div>
      </div>

      <ol className="mt-3 grid gap-2 sm:grid-cols-2" aria-label="Document analysis stages">
        {rows.map((stage) => {
          const Icon = stage.status === 'completed' ? Check : stage.status === 'active' ? LoaderCircle : stage.status === 'failed' ? AlertCircle : Circle;
          return (
            <li key={stage.id} className={`stage-row ${statusClass[stage.status]}`}>
              <Icon className={`h-4 w-4 shrink-0 ${stage.status === 'active' ? 'animate-spin' : ''}`} aria-hidden="true" />
              <span className="min-w-0 flex-1 text-xs font-medium">{stage.label}</span>
              <span className="sr-only">{stage.status}</span>
            </li>
          );
        })}
      </ol>

      {error && <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-800" role="alert">{error}</p>}

      {result && (
        <div className="mt-5 border-t border-slate-200 pt-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-slate-950">Review findings</h3>
            <span className={`status-pill ${result.valid ? 'status-good' : 'status-warn'}`}>
              {result.valid ? 'Checks passed' : 'Follow-up needed'}
            </span>
          </div>
          {result.extraction_message && <p className="mt-2 text-xs leading-5 text-slate-600">{result.extraction_message}</p>}

          {!!Object.keys(result.extracted_fields ?? {}).length && (
            <div className="mt-3">
              <p className="eyebrow">Information read from this file</p>
              <dl className="mt-2 grid gap-2 sm:grid-cols-2">
                {Object.entries(result.extracted_fields ?? {}).map(([key, value]) => (
                  <div key={key} className="rounded-lg border border-slate-200 px-3 py-2">
                    <dt className="text-[11px] capitalize text-slate-500">{key.replace(/_/g, ' ')}</dt>
                    <dd className="mt-0.5 break-words text-xs font-medium text-slate-900">{value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}

          {!!result.checks_passed?.length && <FindingList title="Checks passed" items={result.checks_passed} tone="good" />}
          {!!result.missing_documents.length && <FindingList title="Confirmed missing requirements" items={result.missing_documents} tone="warn" />}
          {!!result.mismatches.length && <FindingList title="Differences to review" items={result.mismatches} tone="danger" />}
          {!!result.fields_unverified.length && <FindingList title="Could not verify from this file" items={result.fields_unverified} tone="neutral" />}

          {result.readiness_score != null && (
            <p className="mt-3 text-xs text-slate-600">
              Claim checklist readiness: <strong className="text-slate-900">{result.readiness_score}%</strong>
              <span> · tracks checklist completion, not approval likelihood.</span>
            </p>
          )}

          {!!result.next_steps.length && <FindingList title="Recommended next steps" items={result.next_steps} tone="neutral" />}
          {result.provider_message && (
            <div className="mt-3 rounded-xl border border-teal-100 bg-teal-50 p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold text-teal-950">Message for your provider</p>
                <button type="button" className="icon-button" onClick={() => void copyProviderMessage()} aria-label="Copy provider message">
                  <Clipboard className="h-4 w-4" /> {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-xs leading-5 text-teal-950">{result.provider_message}</p>
            </div>
          )}
          <p className="mt-3 text-[11px] leading-4 text-slate-500">
            These demo checks help identify paperwork gaps; a complete checklist does not guarantee claim approval.
            {result.provider && ` Response source: ${result.provider === 'groq' ? 'Groq AI' : result.provider === 'replay' ? 'Replay' : 'deterministic fallback'}.`}
          </p>
        </div>
      )}
    </section>
  );
}

function FindingList({ title, items, tone }: { title: string; items: string[]; tone: 'good' | 'warn' | 'danger' | 'neutral' }) {
  const color = tone === 'good' ? 'text-emerald-800' : tone === 'danger' ? 'text-rose-800' : tone === 'warn' ? 'text-amber-900' : 'text-slate-700';
  return (
    <div className="mt-3">
      <p className="eyebrow">{title}</p>
      <ul className={`mt-1.5 space-y-1 text-xs leading-5 ${color}`}>
        {items.map((item) => <li key={item} className="flex gap-2"><span aria-hidden="true">·</span><span>{item}</span></li>)}
      </ul>
    </div>
  );
}
