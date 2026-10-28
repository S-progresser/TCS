import { AnimatePresence, motion } from 'framer-motion';
import { Activity, ArrowRight, BadgeCheck, Bot, FileText, Gauge, MessageSquareText, ShieldCheck, Sparkles, UploadCloud } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { DocumentProgressPanel } from './components/DocumentProgressPanel';
import type { Claim, DocumentReview, DocumentStreamEvent, QueryResponse, RuleBook } from './types';

const apiBase = '/api';

const languageLabels: Record<string, string> = {
  en: 'English',
  hi: 'हिन्दी',
  kn: 'ಕನ್ನಡ',
};

function App() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [selectedClaimId, setSelectedClaimId] = useState('CLM-3021');
  const [query, setQuery] = useState('What are the missing documents for my claim?');
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [rulebooks, setRulebooks] = useState<RuleBook[]>([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [language, setLanguage] = useState('en');
  const [uploadResult, setUploadResult] = useState<DocumentReview | null>(null);
  const [documentEvents, setDocumentEvents] = useState<DocumentStreamEvent[]>([]);
  const [documentError, setDocumentError] = useState<string | null>(null);
  const [documentType, setDocumentType] = useState<string | null>(null);

  const selectedClaim = useMemo(
    () => claims.find((claim) => claim.id === selectedClaimId) ?? claims[0],
    [claims, selectedClaimId],
  );

  useEffect(() => {
    void loadClaims();
    void loadRulebooks();
  }, []);

  const loadClaims = async () => {
    const response = await fetch(`${apiBase}/claims`);
    const data = (await response.json()) as Claim[];
    setClaims(data);
    if (data[0]) setSelectedClaimId(data[0].id);
  };

  const loadRulebooks = async () => {
    const response = await fetch(`${apiBase}/rulebooks`);
    const data = (await response.json()) as RuleBook[];
    setRulebooks(data);
  };

  const submitQuestion = async () => {
    if (!selectedClaim) return;
    setLoading(true);
    setProgress(15);
    try {
      await fetchEventSource(`${apiBase}/chat/stream?claim_id=${selectedClaim.id}`, {
        onmessage(event) {
          const payload = JSON.parse(event.data);
          setProgress(payload.progress ?? 50);
        },
        onclose() {
          setProgress(90);
        },
      });

      const result = await fetch(`${apiBase}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          claim_id: selectedClaim.id,
          question: query,
          language,
        }),
      });
      const data = (await result.json()) as QueryResponse;
      setResponse(data);
      setProgress(100);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const sessionId = crypto.randomUUID();
    const detectedDocumentType = (() => {
      const lower = file.name.toLowerCase();
      if (lower.endsWith('.pdf') || lower.endsWith('.doc') || lower.endsWith('.docx')) return 'document';
      if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return 'image';
      if (lower.endsWith('.txt')) return 'text';
      return 'unknown';
    })();

    setDocumentType(detectedDocumentType);
    setDocumentError(null);
    setUploadResult(null);
    setDocumentEvents([]);

    const streamPromise = fetchEventSource(`${apiBase}/documents/stream?session_id=${sessionId}`, {
      onmessage(event) {
        const payload = JSON.parse(event.data) as DocumentStreamEvent;
        if (!payload.session_id || payload.session_id !== sessionId) return;

        setDocumentEvents((prev) => {
          const next = [...prev];
          const index = next.findIndex((item) => item.stage === payload.stage && item.message === payload.message);
          if (index >= 0) {
            next[index] = payload;
            return next;
          }
          return [...next, payload];
        });
      },
      onerror(error) {
        console.warn('Document stream error:', error);
        setDocumentError('The live document stream disconnected. The final validation result is still available below.');
      },
    });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('filename', file.name);
    formData.append('session_id', sessionId);
    formData.append('claim_id', selectedClaim?.id ?? 'CLM-3021');

    try {
      const result = await fetch(`${apiBase}/documents/process`, {
        method: 'POST',
        body: formData,
      });
      const data = (await result.json()) as DocumentReview;
      setUploadResult(data);

      if (!result.ok) {
        setDocumentError('The backend could not process the upload.');
      }
    } catch (error) {
      console.error('Upload failed', error);
      setDocumentError('The document could not be processed. Please try again.');
    } finally {
      await streamPromise.catch(() => undefined);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <header className="mb-8 flex flex-col gap-4 rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl shadow-cyan-950/30 backdrop-blur">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-cyan-500/15 p-3 text-cyan-300">
                <ShieldCheck className="h-7 w-7" />
              </div>
              <div>
                <p className="text-sm uppercase tracking-[0.22em] text-slate-400">AI-powered claims advisor</p>
                <h1 className="text-3xl font-bold">ClaimSense</h1>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-sm text-cyan-200">
              <Sparkles className="h-4 w-4" />
              Live claim intelligence
            </div>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_2fr]">
          <aside className="space-y-6 rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
            <div>
              <p className="mb-2 text-xs uppercase tracking-[0.2em] text-slate-400">Open claims</p>
              <div className="space-y-3">
                {claims.map((claim) => (
                  <button
                    key={claim.id}
                    onClick={() => setSelectedClaimId(claim.id)}
                    className={`w-full rounded-2xl border p-4 text-left transition ${
                      selectedClaim?.id === claim.id
                        ? 'border-cyan-400 bg-cyan-500/10 shadow-lg shadow-cyan-500/10'
                        : 'border-slate-800 bg-slate-950/40 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-100">{claim.id}</span>
                      <span className="rounded-full bg-slate-800 px-2 py-1 text-[10px] uppercase text-slate-300">
                        {claim.status}
                      </span>
                    </div>
                    <div className="mt-2 text-sm text-slate-300">{claim.customer_name}</div>
                    <div className="mt-1 text-xs text-slate-400">{claim.product}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-200">Readiness score</span>
                <Gauge className="h-4 w-4 text-cyan-300" />
              </div>
              <div className="mb-2 text-3xl font-bold text-cyan-300">
                {selectedClaim?.analysis?.readiness_score ?? 78}%
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${selectedClaim?.analysis?.readiness_score ?? 78}%` }}
                  transition={{ duration: 0.6 }}
                  className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-emerald-400"
                />
              </div>
              <div className="mt-4 space-y-2 text-sm text-slate-300">
                {(selectedClaim?.analysis?.checklist ?? ['Hospital discharge summary submitted', 'KYC verification complete']).map((item) => (
                  <div key={item} className="flex items-center gap-2">
                    <BadgeCheck className="h-4 w-4 text-emerald-400" />
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </aside>

          <main className="space-y-6">
            <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
              <div className="mb-4 flex items-center justify-between gap-2">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Selected claim</p>
                  <h2 className="text-2xl font-bold text-white">{selectedClaim?.id ?? 'CLM-3021'}</h2>
                </div>
                <div className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-sm text-emerald-300">
                  {selectedClaim?.status ?? 'Document review'}
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
                  <div className="mb-2 text-xs uppercase tracking-[0.2em] text-slate-400">Claim amount</div>
                  <div className="text-2xl font-semibold">₹{selectedClaim?.claim_amount?.toLocaleString('en-IN') ?? '1,85,000'}</div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
                  <div className="mb-2 text-xs uppercase tracking-[0.2em] text-slate-400">Deductible</div>
                  <div className="text-2xl font-semibold">₹{selectedClaim?.analysis?.deductible?.toLocaleString('en-IN') ?? '18,000'}</div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
                  <div className="mb-2 text-xs uppercase tracking-[0.2em] text-slate-400">Estimated payout</div>
                  <div className="text-2xl font-semibold">₹{selectedClaim?.analysis?.estimated_payout?.toLocaleString('en-IN') ?? '1,61,000'}</div>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/40 p-4 text-slate-300">
                {selectedClaim?.summary ?? 'No claim summary available.'}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="h-5 w-5 text-cyan-300" />
                  <h3 className="text-xl font-semibold">Insurance assistant</h3>
                </div>
                <select
                  value={language}
                  onChange={(event) => setLanguage(event.target.value)}
                  className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
                >
                  {Object.entries(languageLabels).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-3 md:flex-row">
                <textarea
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  className="min-h-[110px] flex-1 rounded-2xl border border-slate-700 bg-slate-950 p-4 text-slate-100 outline-none ring-0 transition focus:border-cyan-400"
                  placeholder="Ask about coverage, missing documents, or next actions"
                />
                <button
                  onClick={() => void submitQuestion()}
                  disabled={loading}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl bg-cyan-500 px-5 py-3 font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <MessageSquareText className="h-4 w-4" />
                  {loading ? 'Investigating...' : 'Ask ClaimSense'}
                </button>
              </div>

              <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/30 p-4">
                <div className="mb-2 flex items-center justify-between text-sm text-slate-300">
                  <span>Processing</span>
                  <span>{progress}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.3 }}
                    className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-blue-400 to-emerald-400"
                  />
                </div>
              </div>

              <AnimatePresence mode="wait">
                {response && (
                  <motion.div
                    key={response.answer}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="mt-5 rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4"
                  >
                    <div className="mb-2 flex items-center gap-2 text-cyan-200">
                      <Activity className="h-4 w-4" />
                      Explanation
                    </div>
                    <p className="leading-7 text-slate-200">{response.answer}</p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {response.next_actions.map((step) => (
                        <span key={step} className="rounded-full border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-300">
                          {step}
                        </span>
                      ))}
                    </div>
                    <div className="mt-4 text-sm text-slate-300">
                      Confidence: <span className="font-semibold text-white">{(response.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="mt-4 text-sm text-slate-400">
                      Sources: {response.citations.join(', ')}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </section>

            <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
              <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
                <div className="mb-4 flex items-center gap-2">
                  <UploadCloud className="h-5 w-5 text-violet-300" />
                  <h3 className="text-xl font-semibold">Document review</h3>
                </div>
                <input
                  type="file"
                  onChange={handleUpload}
                  className="mb-5 block w-full rounded-2xl border border-dashed border-slate-700 bg-slate-950 p-4 text-sm text-slate-300"
                />

                <DocumentProgressPanel
                  filename={uploadResult?.filename ?? documentEvents[0]?.filename ?? null}
                  documentType={documentType}
                  events={documentEvents}
                  result={uploadResult}
                  error={documentError}
                />
              </section>

              <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
                <div className="mb-4 flex items-center gap-2">
                  <FileText className="h-5 w-5 text-amber-300" />
                  <h3 className="text-xl font-semibold">Rulebook</h3>
                </div>
                <div className="space-y-3">
                  {rulebooks.slice(0, 3).map((rule) => (
                    <div key={rule.id} className="rounded-2xl border border-slate-800 bg-slate-950/40 p-3">
                      <div className="mb-1 text-sm font-semibold text-cyan-200">{rule.title}</div>
                      <div className="text-xs uppercase tracking-[0.2em] text-slate-400">{rule.category}</div>
                      <p className="mt-2 text-sm text-slate-300">{rule.summary}</p>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

export default App;
