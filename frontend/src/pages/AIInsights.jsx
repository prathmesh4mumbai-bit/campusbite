import { useRef, useState } from 'react';
import { api } from '../api/client';
import { ErrorMessage } from '../components/ui';
import { EXAMPLE_QUESTIONS } from '../utils/constants';

export default function AIInsights() {
  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]); // [{ question, answer, orders }]
  const endRef = useRef(null);

  async function ask(text) {
    const q = (text ?? question).trim();
    setBusy(true);
    setError('');
    try {
      // An empty question asks the backend for its default "summary of recent orders".
      const result = await api.post('/ai/insights', { question: q || null });
      setHistory((h) => [...h, { question: q || 'Summary of my recent orders', answer: result.answer, orders: result.orders_considered }]);
      setQuestion('');
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    } catch (err) {
      setError(err.status === 429 ? `${err.message}${err.retryAfter ? ` (try again in ~${err.retryAfter}s)` : ''}` : err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="narrow">
      <h1>AI order insights</h1>
      <p className="muted">
        Ask questions about <strong>your own</strong> order history. Answers are generated from your actual orders only.
      </p>

      <div className="chips">
        {EXAMPLE_QUESTIONS.map((example) => (
          <button key={example} type="button" className="chip" disabled={busy} onClick={() => ask(example)}>
            {example}
          </button>
        ))}
      </div>

      <div className="chat" aria-live="polite">
        {history.map((item, index) => (
          <div key={index} className="chat-turn">
            <div className="bubble bubble-user">{item.question}</div>
            <div className="bubble bubble-ai">
              <p className="pre">{item.answer}</p>
              <small className="muted">Based on {item.orders} order{item.orders === 1 ? '' : 's'}</small>
            </div>
          </div>
        ))}
        {busy && (
          <div className="bubble bubble-ai">
            <span className="spinner" aria-hidden="true" /> Thinking...
          </div>
        )}
        <div ref={endRef} />
      </div>

      <ErrorMessage message={error} />

      <form
        className="card ask-form"
        onSubmit={(e) => {
          e.preventDefault();
          ask();
        }}
      >
        <label>
          Your question
          <textarea
            rows={2}
            maxLength={500}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. How much did I spend this week?"
          />
        </label>
        <div className="row">
          <span className="muted small">{question.length}/500</span>
          <button className="btn" type="submit" disabled={busy}>
            {busy ? 'Asking...' : question.trim() ? 'Ask' : 'Summarize my recent orders'}
          </button>
        </div>
      </form>
    </section>
  );
}
