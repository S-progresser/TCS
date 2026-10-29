import { fetchEventSource } from '@microsoft/fetch-event-source';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Activity, ArrowDownToLine, ArrowRight, BadgeCheck, Bot, Check, ChevronDown, CircleHelp,
  ClipboardList, FileCheck2, FileText, Gauge, Languages, LoaderCircle, MessageSquareText,
  RotateCcw, ShieldCheck, Sparkles, UploadCloud, X,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { DocumentProgressPanel } from './components/DocumentProgressPanel';
import { isTerminalDocumentEvent } from './types';
import type { Claim, DocumentReview, DocumentStreamEvent, ProviderStatus, QueryResponse, RuleBook } from './types';

const apiBase = '/api';
const languageLabels: Record<string, string> = { en: 'English', hi: 'हिन्दी', kn: 'ಕನ್ನಡ' };
const allowedExtensions = ['pdf', 'jpg', 'jpeg', 'png'];
const maxUploadBytes = 10 * 1024 * 1024;
const documentAnalysisTimeoutMs = 60_000;

type UploadItem = { name: string; size: number; status: 'selected' | 'processing' | 'reviewed' | 'failed'; error?: string };

function App() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [claim, setClaim] = useState<Claim | null>(null);
  const [rulebooks, setRulebooks] = useState<RuleBook[]>([]);
  const [provider, setProvider] = useState<ProviderStatus | null>(null);
  const [language, setLanguage] = useState('en');
  const [query, setQuery] = useState('What is the current status of my claim?');
  const [answer, setAnswer] = useState<QueryResponse | null>(null);
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [uploadItem, setUploadItem] = useState<UploadItem | null>(null);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [review, setReview] = useState<DocumentReview | null>(null);
  const [previousReview, setPreviousReview] = useState<DocumentReview | null>(null);
  const [events, setEvents] = useState<DocumentStreamEvent[]>([]);
  const [dragging, setDragging] = useState(false);
  const [showWarRoom, setShowWarRoom] = useState(false);
  const [replayMode, setReplayMode] = useState(false);
  const [replaySteps, setReplaySteps] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);
  const sessionRef = useRef<string | null>(null);
  const streamControllerRef = useRef<AbortController | null>(null);
  const requestControllerRef = useRef<AbortController | null>(null);
  const eventsRef = useRef<DocumentStreamEvent[]>([]);
  const fileListId = 'uploaded-document-list';

  const selectedRulebook = useMemo(() => {
    if (!claim) return undefined;
    const category = claim.product.toLowerCase().includes('motor') ? 'motor' : 'documents';
    return rulebooks.find((rule) => rule.category === category) ?? rulebooks.find((rule) => rule.category === 'coverage');
  }, [claim, rulebooks]);

  const loadClaim = useCallback(async (claimId: string) => {
    const response = await fetch(`${apiBase}/claims/${encodeURIComponent(claimId)}`);
    if (!response.ok) throw new Error('Claim details could not be loaded.');
    setClaim((await response.json()) as Claim);
  }, []);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const [claimsResponse, rulesResponse, healthResponse] = await Promise.all([
          fetch(`${apiBase}/claims`), fetch(`${apiBase}/rulebooks`), fetch(`${apiBase}/health`),
        ]);
        if (!claimsResponse.ok || !rulesResponse.ok || !healthResponse.ok) throw new Error('The ClaimSense service is unavailable.');
        const claimList = (await claimsResponse.json()) as Claim[];
        if (!active) return;
        setClaims(claimList);
        setRulebooks((await rulesResponse.json()) as RuleBook[]);
        setProvider((await healthResponse.json()) as ProviderStatus);
        if (claimList[0]) await loadClaim(claimList[0].id);
      } catch (error) {
        if (active) setUploadError(error instanceof Error ? error.message : 'The ClaimSense service is unavailable.');
      } finally {
        if (active) setIsLoading(false);
      }
    };
    void load();
    return () => {
      active = false;
      streamControllerRef.current?.abort();
      requestControllerRef.current?.abort();
    };
  }, [loadClaim]);

  const chooseClaim = async (claimId: string) => {
    streamControllerRef.current?.abort();
    requestControllerRef.current?.abort();
    sessionRef.current = null;
    setUploadBusy(false);
    if (review) setPreviousReview(review);
    setReview(null);
    setCurrentFile(null);
    setUploadItem(null);
    setEvents([]);
    eventsRef.current = [];
    setAnswer(null);
    setChatError(null);
    setUploadError(null);
    try {
      await loadClaim(claimId);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Claim details could not be loaded.');
    }
  };

  const acceptFile = (file?: File) => {
    if (!file) return;
    const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (!allowedExtensions.includes(extension)) {
      setUploadError('Choose a PDF, JPG, JPEG, or PNG file.');
      return;
    }
    if (file.size > maxUploadBytes) {
      setUploadError('The maximum file size is 10 MB.');
      return;
    }
    if (!claim) {
      setUploadError('Select a claim before choosing a document.');
      return;
    }
    streamControllerRef.current?.abort();
    requestControllerRef.current?.abort();
    sessionRef.current = null;
    setUploadBusy(false);
    if (review) setPreviousReview(review);
    setReview(null);
    setEvents([]);
    eventsRef.current = [];
    setUploadError(null);
    setCurrentFile(file);
    setUploadItem({ name: file.name, size: file.size, status: 'selected' });
  };

  const updateEvents = (event: DocumentStreamEvent, expectedSession: string) => {
    if (!event.session_id || event.session_id !== expectedSession || sessionRef.current !== expectedSession) return;
    const key = `${event.type}:${event.stage}:${event.status}:${event.message}`;
    if (eventsRef.current.some((item) => `${item.type}:${item.stage}:${item.status}:${item.message}` === key)) return;
    const next = [...eventsRef.current, event];
    eventsRef.current = next;
    setEvents(next);
    if (event.result) setReview(event.result);
    if (isTerminalDocumentEvent(event)) {
      setUploadBusy(false);
      if (event.type === 'document.failed') {
        const message = event.details || event.message || 'Document analysis failed. Please retry.';
        setUploadError(message);
        setUploadItem((item) => item ? { ...item, status: 'failed', error: message } : item);
      } else {
        setUploadItem((item) => item ? { ...item, status: 'reviewed', error: undefined } : item);
      }
      streamControllerRef.current?.abort();
      requestControllerRef.current?.abort();
    }
  };

  const markAnalysisFailed = (sessionId: string, message: string) => {
    const activeStage = [...eventsRef.current].reverse().find((event) => event.status === 'active')?.stage;
    updateEvents({
      type: 'document.failed',
      session_id: sessionId,
      stage: activeStage ?? 'explanation',
      status: 'failed',
      message: 'Document analysis could not be completed',
      details: message,
      error: 'analysis_failed',
    }, sessionId);
  };

  const startAnalysis = async () => {
    if (!currentFile || !claim || uploadBusy) return;
    const sessionId = crypto.randomUUID();
    sessionRef.current = sessionId;
    const controller = new AbortController();
    const requestController = new AbortController();
    streamControllerRef.current?.abort();
    requestControllerRef.current?.abort();
    streamControllerRef.current = controller;
    requestControllerRef.current = requestController;
    let streamRetries = 0;
    let timedOut = false;
    const timeoutId = window.setTimeout(() => {
      if (sessionRef.current !== sessionId) return;
      timedOut = true;
      const message = 'Document analysis timed out. Please retry.';
      setUploadError(message);
      setUploadItem((item) => item ? { ...item, status: 'failed', error: message } : item);
      markAnalysisFailed(sessionId, message);
      setUploadBusy(false);
      controller.abort();
      requestController.abort();
    }, documentAnalysisTimeoutMs);
    setUploadBusy(true);
    setUploadError(null);
    setUploadItem({ name: currentFile.name, size: currentFile.size, status: 'processing' });

    const streamPromise = fetchEventSource(
      `${apiBase}/documents/stream?session_id=${encodeURIComponent(sessionId)}`,
      {
        signal: controller.signal,
        openWhenHidden: true,
        async onopen(response) {
          if (!response.ok) throw new Error(`Live progress connection failed (${response.status}).`);
        },
        onmessage(message) {
          try {
            const event = JSON.parse(message.data) as DocumentStreamEvent;
            updateEvents(event, sessionId);
          } catch {
            setUploadError('A document progress message could not be read.');
          }
        },
        onclose() { controller.abort(); },
        onerror(error) {
          streamRetries += 1;
          if (streamRetries >= 3) throw error;
          setUploadError('Live updates disconnected. The final analysis response will still be shown if available.');
          return 500 * streamRetries;
        },
      },
    ).catch((error: unknown) => {
      if (!controller.signal.aborted) {
        setUploadError(error instanceof Error ? error.message : 'Live document updates are unavailable.');
      }
    });

    try {
      const form = new FormData();
      form.append('file', currentFile);
      form.append('filename', currentFile.name);
      form.append('claim_id', claim.id);
      form.append('session_id', sessionId);
      const response = await fetch(`${apiBase}/documents/process`, {
        method: 'POST',
        body: form,
        signal: requestController.signal,
      });
      const payload = await response.json() as DocumentReview | { detail?: string };
      if (!response.ok) throw new Error('detail' in payload ? payload.detail ?? 'Document processing failed.' : 'Document processing failed.');
      const result = payload as DocumentReview;
      if (sessionRef.current === sessionId) {
        setReview(result);
        const succeeded = result.extraction_status === 'extracted';
        setUploadItem({
          name: currentFile.name,
          size: currentFile.size,
          status: succeeded ? 'reviewed' : 'failed',
          error: succeeded ? undefined : result.extraction_message ?? 'The document could not be read. Please retry with a clearer file.',
        });
        if (!succeeded) setUploadError(result.extraction_message ?? 'The document could not be read. Please retry with a clearer file.');
        if (!eventsRef.current.some((event) => isTerminalDocumentEvent(event))) {
          updateEvents({
            type: succeeded ? 'document.completed' : 'document.failed',
            session_id: sessionId,
            stage: 'explanation',
            status: succeeded ? 'completed' : 'failed',
            message: succeeded ? 'Document analysis complete' : 'Document analysis could not be completed',
            details: succeeded ? 'The analysis response is ready.' : result.extraction_message ?? 'Upload a clearer document and retry.',
            result,
          }, sessionId);
        }
        setPreviousReview(null);
      }
    } catch (error) {
      const terminalReceived = eventsRef.current.some((event) => isTerminalDocumentEvent(event));
      if (sessionRef.current === sessionId && !timedOut && !terminalReceived) {
        const message = error instanceof Error ? error.message : 'Document processing failed.';
        setUploadError(message);
        setUploadItem((item) => item ? { ...item, status: 'failed', error: message } : item);
        markAnalysisFailed(sessionId, message);
      }
    } finally {
      window.clearTimeout(timeoutId);
      controller.abort();
      requestController.abort();
      void streamPromise;
      if (sessionRef.current === sessionId) setUploadBusy(false);
    }
  };

  const askClaimQuestion = async () => {
    if (!claim || !query.trim() || chatBusy) return;
    setChatBusy(true);
    setChatError(null);
    try {
      const documentContext = review ? JSON.stringify({
        filename: review.filename,
        missing_documents: review.missing_documents,
        mismatches: review.mismatches,
        fields_missing: review.fields_missing,
        fields_unverified: review.fields_unverified,
        checks_passed: review.checks_passed,
        extraction_status: review.extraction_status,
        provider_message: review.provider_message,
      }) : undefined;
      const response = await fetch(`${apiBase}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          claim_id: claim.id,
          question: query,
          language,
          document_context: documentContext,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? 'The question could not be answered.');
      setAnswer(payload as QueryResponse);
    } catch (error) {
      setChatError(error instanceof Error ? error.message : 'The question could not be answered.');
    } finally {
      setChatBusy(false);
    }
  };

  const openReplay = async () => {
    try {
      const response = await fetch(`${apiBase}/replay`);
      if (!response.ok) throw new Error('Replay mode is unavailable.');
      const payload = await response.json() as { mode: string; steps: string[] };
      setReplayMode(payload.mode === 'replay');
      setReplaySteps(payload.steps);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Replay mode is unavailable.');
    }
  };

  const removeSelectedFile = () => {
    streamControllerRef.current?.abort();
    requestControllerRef.current?.abort();
    sessionRef.current = null;
    setUploadBusy(false);
    setCurrentFile(null);
    setUploadItem(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const readiness = claim?.analysis?.readiness_score;
  const statusLabel = provider?.state === 'configured' ? 'Groq connected' : provider?.state === 'replay' ? 'Replay mode' : 'Deterministic demo';

  return (
    <div className="app-shell min-h-screen text-slate-900">
      <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
          <a href="#" className="flex items-center gap-2.5 rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-700" aria-label="ClaimSense home">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-teal-800 text-white"><ShieldCheck className="h-5 w-5" /></span>
            <span><span className="block text-base font-bold tracking-tight text-slate-950">ClaimSense</span><span className="hidden text-[10px] font-medium uppercase tracking-[.15em] text-slate-500 sm:block">Insurance claim assistant</span></span>
          </a>
          <div className="flex items-center gap-2 sm:gap-3">
            <span className={`hidden items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold sm:inline-flex ${provider?.state === 'configured' ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-900'}`}>
              <span className="h-1.5 w-1.5 rounded-full bg-current" />{statusLabel}
            </span>
            <label className="sr-only" htmlFor="language-select">Choose language</label>
            <span className="hidden text-slate-500 sm:block"><Languages className="h-4 w-4" /></span>
            <select id="language-select" value={language} onChange={(event) => setLanguage(event.target.value)} className="control-select max-w-32">
              {Object.entries(languageLabels).map(([key, value]) => <option value={key} key={key}>{value}</option>)}
            </select>
            <button type="button" className="button-secondary !px-3 !py-2" onClick={() => void openReplay()} title="Open the clearly labeled demo replay">
              <RotateCcw className="h-4 w-4" /><span className="hidden sm:inline">Replay</span>
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-5 px-4 py-5 sm:px-6 sm:py-7 lg:px-8">
        {uploadError && !uploadBusy && (
          <div className="flex items-start justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">
            <span>{uploadError}</span><button type="button" className="rounded p-1 hover:bg-rose-100" onClick={() => setUploadError(null)} aria-label="Dismiss error"><X className="h-4 w-4" /></button>
          </div>
        )}

        <section className="surface-card overflow-hidden">
          <div className="flex flex-col gap-5 p-5 sm:p-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="eyebrow">Selected claim</p>
                {claim && <span className="status-pill status-neutral">{claim.id}</span>}
                {claim && <span className="status-pill status-warn">{claim.status}</span>}
              </div>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">{claim?.product ?? 'Your claim overview'}</h1>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">{claim?.summary ?? 'Choose a claim to review its status and documents.'}</p>
              <p className="mt-2 text-xs text-slate-500">{claim?.customer_name} {claim?.branch ? `· ${claim.branch}` : ''} {claim?.insurer ? `· ${claim.insurer}` : ''}</p>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <label htmlFor="claim-select" className="eyebrow mb-1.5 block">Switch claim</label>
                <div className="relative">
                  <select id="claim-select" value={claim?.id ?? ''} onChange={(event) => void chooseClaim(event.target.value)} className="control-select min-w-48 pr-9">
                    {claims.map((item) => <option value={item.id} key={item.id}>{item.id} · {item.customer_name}</option>)}
                  </select><ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                </div>
              </div>
              <div className="rounded-xl bg-slate-50 px-4 py-2.5">
                <p className="eyebrow">Claim amount</p><p className="mt-0.5 text-lg font-semibold tabular-nums text-slate-950">{claim ? formatCurrency(claim.claim_amount) : '—'}</p>
              </div>
              <div className="rounded-xl bg-slate-50 px-4 py-2.5">
                <p className="eyebrow">Checklist readiness</p><p className="mt-0.5 text-lg font-semibold tabular-nums text-teal-800">{readiness == null ? '—' : `${readiness}%`}</p>
              </div>
            </div>
          </div>
          <div className="grid gap-px border-t border-slate-200 bg-slate-200 sm:grid-cols-3">
            <Metric label="Deductible" value={claim ? formatCurrency(claim.analysis?.deductible) : '—'} />
            <Metric label="Co-pay" value={claim ? formatCurrency(claim.analysis?.copay) : '—'} />
            <Metric label="Illustrative payout" value={claim ? formatCurrency(claim.analysis?.estimated_payout) : '—'} note="Not an approved payment amount" />
          </div>
          <div className="flex items-center gap-2 px-5 py-2.5 text-[11px] text-slate-500 sm:px-6">
            <CircleHelp className="h-3.5 w-3.5 shrink-0" /> Readiness tracks the listed checklist only. It is not a prediction or guarantee of claim approval.
          </div>
        </section>

        <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(330px,.85fr)]">
          <div className="space-y-5">
            <section className="surface-card p-5 sm:p-6" aria-labelledby="upload-heading">
              <div className="mb-4 flex items-start justify-between gap-4">
                <div><p className="eyebrow">Secure document review</p><h2 id="upload-heading" className="mt-1 text-xl font-semibold text-slate-950">Add a claim document</h2><p className="mt-1 text-sm text-slate-600">Upload a PDF or a clear JPG/PNG image. Files are checked against this selected claim.</p></div>
                <div className="hidden rounded-xl bg-teal-50 p-2.5 text-teal-800 sm:block"><UploadCloud className="h-5 w-5" /></div>
              </div>
              <input ref={inputRef} id="document-file" type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" className="sr-only" onChange={(event) => acceptFile(event.target.files?.[0])} />
              <label
                htmlFor="document-file"
                onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={(event) => { event.preventDefault(); setDragging(false); acceptFile(event.dataTransfer.files[0]); }}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    inputRef.current?.click();
                  }
                }}
                className={`upload-zone ${dragging ? 'upload-zone-active' : ''}`}
              >
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-white text-teal-800 shadow-sm"><UploadCloud className="h-5 w-5" /></span>
                <span className="text-sm font-semibold text-slate-900">{dragging ? 'Drop the file to add it' : 'Drop a file here or browse'}</span>
                <span className="text-xs text-slate-500">PDF, JPG, JPEG, PNG · up to 10 MB · one file per review</span>
              </label>

              {uploadItem && (
                <ul id={fileListId} className="mt-3 space-y-2" aria-label="Uploaded files">
                  <li className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5">
                    <span className="flex min-w-0 items-center gap-2.5">
                      <FileText className="h-4 w-4 shrink-0 text-teal-800" />
                      <span className="min-w-0"><span className="block truncate text-sm font-medium text-slate-900">{uploadItem.name}</span><span className="text-[11px] text-slate-500">{formatBytes(uploadItem.size)} · {uploadItem.status === 'selected' ? 'Selected, not yet analyzed' : uploadItem.status === 'processing' ? 'Uploading and analyzing' : uploadItem.status === 'reviewed' ? 'Analysis returned' : uploadItem.error ?? 'Needs attention'}</span></span>
                    </span>
                    <div className="flex items-center gap-2">
                      {uploadItem.status === 'selected' && <button type="button" className="button-primary !py-2" onClick={() => void startAnalysis()} disabled={!claim}><ArrowRight className="h-4 w-4" />Analyze file</button>}
                      {uploadItem.status === 'failed' && <button type="button" className="button-primary !py-2" onClick={() => void startAnalysis()} disabled={!claim || uploadBusy}><RotateCcw className="h-4 w-4" />Retry</button>}
                      {uploadItem.status === 'processing' && <span className="inline-flex items-center gap-1.5 text-xs font-medium text-teal-800"><LoaderCircle className="h-4 w-4 animate-spin" />Processing</span>}
                      {uploadItem.status === 'reviewed' && <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-800"><Check className="h-4 w-4" />Reviewed</span>}
                      <button type="button" className="icon-button" disabled={uploadBusy} onClick={removeSelectedFile} aria-label="Remove selected file"><X className="h-4 w-4" /></button>
                    </div>
                  </li>
                </ul>
              )}
            </section>

            <DocumentProgressPanel
              filename={currentFile?.name ?? review?.filename ?? null}
              documentType={review?.extracted_document_type ?? (currentFile?.type.startsWith('image/') ? 'image' : currentFile ? 'PDF document' : null)}
              events={events}
              result={review}
              error={uploadError}
              processing={uploadBusy}
            />

            {previousReview && (
              <details className="surface-card p-4">
                <summary className="cursor-pointer text-sm font-medium text-slate-700">Previous analysis for {previousReview.filename} · {previousReview.claim_id ?? 'previous claim'}</summary>
                <p className="mt-2 text-xs text-slate-600">This is an earlier result and does not apply to the currently selected file or claim.</p>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate-600">{previousReview.next_steps.map((step) => <li key={step}>{step}</li>)}</ul>
              </details>
            )}

            <section className="surface-card p-5 sm:p-6">
              <div className="flex items-center justify-between gap-3"><div><p className="eyebrow">Claim support</p><h2 className="mt-1 text-lg font-semibold text-slate-950">Ask about this claim</h2></div><Bot className="h-5 w-5 text-teal-800" /></div>
              <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                <label className="sr-only" htmlFor="claim-question">Question about your claim</label>
                <textarea id="claim-question" value={query} onChange={(event) => setQuery(event.target.value)} className="control-input min-h-20 flex-1 resize-y" placeholder="Ask about claim status, coverage or next steps" />
                <button type="button" className="button-primary self-stretch sm:self-end" onClick={() => void askClaimQuestion()} disabled={chatBusy || !claim || !query.trim()}><MessageSquareText className="h-4 w-4" />{chatBusy ? 'Checking…' : 'Ask ClaimSense'}</button>
              </div>
              {chatError && <p className="mt-2 text-sm text-rose-700" role="alert">{chatError}</p>}
              <AnimatePresence mode="wait">
                {answer && (
                  <motion.div key={answer.answer} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="mt-4 rounded-xl border border-teal-100 bg-teal-50/60 p-4">
                    <div className="flex items-center justify-between gap-2"><p className="flex items-center gap-2 text-sm font-semibold text-slate-950"><Sparkles className="h-4 w-4 text-teal-800" />Claim explanation</p><span className="status-pill status-neutral">{answer.provider === 'groq' ? 'Groq' : answer.provider === 'gemini' ? 'Gemini' : answer.provider === 'replay' ? 'Replay' : 'Fallback'}</span></div>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{answer.answer}</p>
                    {!!answer.next_actions.length && <ul className="mt-3 space-y-1 text-xs text-slate-700">{answer.next_actions.map((action) => <li key={action} className="flex gap-2"><ArrowRight className="mt-0.5 h-3 w-3 shrink-0 text-teal-800" />{action}</li>)}</ul>}
                    {!!answer.citations.length && <div className="mt-3 border-t border-teal-100 pt-2"><p className="eyebrow">Retrieved evidence · demo knowledge base</p><ul className="mt-1 space-y-1 text-xs text-slate-600">{answer.citations.map((citation) => <li key={citation}>{citation}</li>)}</ul></div>}
                    {!answer.citations.length && <p className="mt-2 text-xs text-slate-500">No matching source was retrieved; this explanation is limited to the claim record.</p>}
                  </motion.div>
                )}
              </AnimatePresence>
            </section>
          </div>

          <aside className="space-y-5">
            <section className="surface-card p-5">
              <div className="flex items-center justify-between gap-3">
                <div><p className="eyebrow">Claim checklist</p><h2 className="mt-1 text-base font-semibold text-slate-950">Readiness, not approval</h2></div><Gauge className="h-5 w-5 text-teal-800" />
              </div>
              {readiness == null ? <p className="mt-3 text-sm text-slate-500">Checklist readiness is not available for this claim.</p> : (
                <>
                  <div className="mt-4 flex items-end justify-between"><span className="text-3xl font-semibold tabular-nums text-slate-950">{readiness}%</span><span className="text-xs text-slate-500">items marked complete</span></div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-teal-700 transition-all" style={{ width: `${readiness}%` }} /></div>
                  <ul className="mt-3 space-y-2">{(claim?.analysis?.checklist ?? []).map((item) => <li key={item} className="flex items-start gap-2 text-xs text-slate-700"><BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" />{item}</li>)}</ul>
                  {(claim?.analysis?.next_steps ?? []).length > 0 && <div className="mt-3 border-t border-slate-100 pt-3"><p className="eyebrow">Still outstanding</p><ul className="mt-2 space-y-2">{claim?.analysis?.next_steps.map((item) => <li key={item} className="flex items-start gap-2 text-xs text-amber-900"><ClipboardList className="mt-0.5 h-3.5 w-3.5 shrink-0" />{item.replace(/^Complete:\s*/, '')}</li>)}</ul></div>}
                </>
              )}
              <p className="mt-3 text-[11px] leading-4 text-slate-500">Based on checklist entries in synthetic demo claim data. A completed checklist does not establish coverage or guarantee settlement.</p>
            </section>

            <section className="surface-card p-5">
              <div className="flex items-center justify-between gap-2"><div><p className="eyebrow">Claim activity</p><h2 className="mt-1 text-base font-semibold text-slate-950">History & War Room</h2></div><Activity className="h-5 w-5 text-indigo-700" /></div>
              <p className="mt-2 text-xs leading-5 text-slate-600">Live document workflow events appear in the War Room. Claim history is not included in this demo record.</p>
              <button type="button" className="button-secondary mt-3 w-full justify-between" onClick={() => setShowWarRoom((value) => !value)} aria-expanded={showWarRoom}> {showWarRoom ? 'Hide War Room' : 'Open War Room'} <ArrowDownToLine className={`h-4 w-4 transition-transform ${showWarRoom ? 'rotate-180' : ''}`} /></button>
              {showWarRoom && (
                <div className="mt-3 rounded-xl bg-slate-50 p-3">
                  <p className="eyebrow">Workflow event log</p>
                  {events.length ? <ol className="mt-2 space-y-2">{events.map((event, index) => <li key={`${event.session_id}-${event.stage}-${event.status}-${index}`} className="flex gap-2 text-xs"><span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${event.status === 'failed' ? 'bg-rose-500' : event.status === 'completed' ? 'bg-emerald-600' : 'bg-teal-600'}`} /><span><strong className="text-slate-800">{event.message}</strong><span className="block text-slate-500">{event.details}</span></span></li>)}</ol> : <p className="mt-2 text-xs text-slate-500">No processing events yet.</p>}
                  <p className="mt-3 border-t border-slate-200 pt-2 text-[10px] leading-4 text-slate-500">Workflow stages are not separate AI agents. ClaimSense uses Concierge, Claim & Policy Investigator, Document Analyst, and Explainer & Verifier.</p>
                </div>
              )}
            </section>

            {selectedRulebook && (
              <section className="surface-card p-5">
                <div className="flex items-center justify-between gap-2"><div><p className="eyebrow">Supporting information</p><h2 className="mt-1 text-base font-semibold text-slate-950">Applicable demo rules</h2></div><FileCheck2 className="h-5 w-5 text-teal-800" /></div>
                <div className="mt-3 rounded-xl border border-slate-200 p-3">
                  <p className="text-sm font-semibold text-slate-900">{selectedRulebook.title}</p>
                  <p className="mt-1 text-[11px] text-slate-500">{selectedRulebook.source} · synthetic demo rulebook</p>
                  <p className="mt-2 text-xs leading-5 text-slate-600">{selectedRulebook.summary}</p>
                </div>
                {!!selectedRulebook.required_documents?.length && <ul className="mt-3 space-y-1.5">{selectedRulebook.required_documents.map((item) => <li className="flex gap-2 text-xs text-slate-700" key={item}><FileText className="h-3.5 w-3.5 shrink-0 text-slate-400" />{item}</li>)}</ul>}
                <p className="mt-3 text-[11px] leading-4 text-slate-500">These configured demo rules are not a substitute for the customer&apos;s actual policy wording.</p>
              </section>
            )}

            {replayMode && (
              <section className="rounded-2xl border border-indigo-200 bg-indigo-50 p-4">
                <div className="flex items-center justify-between"><p className="text-sm font-semibold text-indigo-950">Replay · simulated walkthrough</p><button type="button" onClick={() => setReplayMode(false)} aria-label="Close replay"><X className="h-4 w-4" /></button></div>
                <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs text-indigo-900">{replaySteps.map((step) => <li key={step}>{step}</li>)}</ol>
              </section>
            )}
          </aside>
        </div>

        {isLoading && <div className="fixed bottom-4 right-4 inline-flex items-center gap-2 rounded-full bg-white px-3 py-2 text-xs text-slate-600 shadow-lg"><LoaderCircle className="h-4 w-4 animate-spin" />Loading claims</div>}
        <footer className="pb-3 text-center text-[11px] text-slate-500">ClaimSense is a demo assistant. Confirm requirements and claim decisions with your insurer.</footer>
      </main>
    </div>
  );
}

function Metric({ label, value, note }: { label: string; value: string; note?: string }) {
  return <div className="bg-white px-5 py-3"><p className="eyebrow">{label}</p><p className="mt-0.5 text-sm font-semibold tabular-nums text-slate-900">{value}</p>{note && <p className="mt-0.5 text-[10px] text-slate-500">{note}</p>}</div>;
}

function formatCurrency(value?: number | null) {
  if (value == null || !Number.isFinite(value)) return '—';
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);
}

function formatBytes(bytes: number) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default App;
