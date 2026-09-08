import { useEffect, useRef, useState } from "react";
import { AlertTriangle, MessageSquarePlus, PanelRightClose, PanelRightOpen, Send } from "lucide-react";
import { useActivePatient } from "../contexts/PatientContext";
import { chatApi } from "../api/client";
import type { ChatMessage, ChatSession, Citation } from "../types";
import { Button, Spinner } from "../components/ui";
import { openDocumentInNewTab } from "../hooks/useDocumentBlobUrl";

function CitationChip({ citation }: { citation: Citation }) {
  return (
    <button
      onClick={() => openDocumentInNewTab(citation.document_id)}
      className="inline-flex items-center gap-1 rounded-full border border-[var(--color-border)] bg-white px-2 py-0.5 text-[11px] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
      title={citation.snippet}
    >
      {citation.document_name}
      {citation.page ? ` p.${citation.page}` : ""}
    </button>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-lg px-3.5 py-2.5 text-sm whitespace-pre-wrap ${
          isUser ? "bg-[var(--color-accent)] text-white" : "bg-white border border-[var(--color-border)]"
        }`}
      >
        {message.pending_curation_flag && !isUser && (
          <div className="flex items-center gap-1.5 mb-1.5 text-[11px] text-[var(--color-warning)]">
            <AlertTriangle size={12} /> Based partly on records still pending curator review
          </div>
        )}
        <div>{message.content}</div>
        {!isUser && message.citations.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {message.citations.map((c, i) => (
              <CitationChip key={i} citation={c} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function PatientChatPage() {
  const { patient } = useActivePatient();
  const [sessions, setSessions] = useState<ChatSession[] | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [starters, setStarters] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [showSources, setShowSources] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  // onDone's closure captures streamText's value at the time `send` was
  // called (empty string), not the final streamed text -- track the latest
  // chunk total in a ref so onDone can read the up-to-date value.
  const streamTextRef = useRef("");

  useEffect(() => {
    if (!patient) return;
    chatApi.listSessions(patient.id).then((s) => {
      setSessions(s);
      if (s.length > 0) setActiveSessionId(s[0].id);
    });
    chatApi.starters(patient.id).then((r) => setStarters(r.starters));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patient?.id]);

  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      return;
    }
    chatApi.messages(activeSessionId).then(setMessages);
  }, [activeSessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streamText]);

  async function newConversation() {
    if (!patient) return;
    const session = await chatApi.createSession(patient.id);
    setSessions((s) => [session, ...(s || [])]);
    setActiveSessionId(session.id);
    setMessages([]);
  }

  async function send(question: string) {
    if (!question.trim() || streaming) return;
    let sessionId = activeSessionId;
    if (!sessionId && patient) {
      const session = await chatApi.createSession(patient.id);
      setSessions((s) => [session, ...(s || [])]);
      sessionId = session.id;
      setActiveSessionId(sessionId);
    }
    if (!sessionId) return;

    setMessages((m) => [
      ...m,
      {
        id: `temp-user-${Date.now()}`,
        role: "user",
        content: question,
        citations: [],
        pending_curation_flag: false,
        created_at: new Date().toISOString(),
      },
    ]);
    setInput("");
    setStreaming(true);
    setStreamText("");

    await chatApi.ask(sessionId, question, {
      onDelta: (chunk) => setStreamText((t) => t + chunk),
      onDone: (result) => {
        setMessages((m) => [
          ...m,
          {
            id: result.message_id,
            role: "assistant",
            content: streamTextRef.current,
            citations: result.citations,
            pending_curation_flag: result.pending_curation_flag,
            created_at: new Date().toISOString(),
          },
        ]);
        setStreamText("");
        setStreaming(false);
      },
      onError: () => {
        setStreaming(false);
        setStreamText("");
      },
    });
  }

  useEffect(() => {
    streamTextRef.current = streamText;
  }, [streamText]);

  if (!patient) return null;

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");

  return (
    <div className="h-full flex">
      <div className="w-56 shrink-0 border-r border-[var(--color-border)] bg-white p-3 overflow-y-auto">
        <Button size="sm" className="w-full mb-3" onClick={newConversation}>
          <MessageSquarePlus size={14} /> New conversation
        </Button>
        <ul className="space-y-1">
          {sessions?.map((s) => (
            <li key={s.id}>
              <button
                onClick={() => setActiveSessionId(s.id)}
                className={`w-full text-left truncate rounded-md px-2 py-1.5 text-xs ${
                  activeSessionId === s.id ? "bg-[var(--color-accent-bg)] text-[var(--color-accent)]" : "hover:bg-gray-100"
                }`}
              >
                {s.title || "New conversation"}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-5 space-y-3">
          {messages.length === 0 && !streaming && (
            <div className="max-w-md mx-auto text-center pt-10">
              <p className="text-sm text-[var(--color-text-muted)] mb-3">
                Ask a question grounded in {patient.name}'s wiki and documents.
              </p>
              <div className="flex flex-col gap-2">
                {starters.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="rounded-md border border-[var(--color-border)] bg-white px-3 py-2 text-sm text-left hover:border-[var(--color-accent)]"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          {streaming && (
            <div className="flex justify-start">
              <div className="max-w-[75%] rounded-lg px-3.5 py-2.5 text-sm bg-white border border-[var(--color-border)] whitespace-pre-wrap">
                {streamText || <Spinner label="Thinking…" />}
              </div>
            </div>
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="border-t border-[var(--color-border)] bg-white p-3 flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about this patient's records…"
            className="flex-1 rounded-md border border-[var(--color-border)] px-3 py-2 text-sm focus:ring-2 focus:ring-[var(--color-accent)] outline-none"
          />
          <Button type="submit" disabled={streaming || !input.trim()}>
            <Send size={15} />
          </Button>
          <button
            type="button"
            onClick={() => setShowSources((s) => !s)}
            className="rounded-md border border-[var(--color-border)] px-3 text-[var(--color-text-muted)] hover:bg-gray-50"
            title="Toggle sources panel"
          >
            {showSources ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
          </button>
        </form>
      </div>

      {showSources && (
        <aside className="w-72 shrink-0 border-l border-[var(--color-border)] bg-white p-4 overflow-y-auto">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)] mb-3">
            Sources for last answer
          </p>
          {!lastAssistant || lastAssistant.citations.length === 0 ? (
            <p className="text-sm text-[var(--color-text-muted)]">No sources yet — ask a question to see citations here.</p>
          ) : (
            <ul className="space-y-3">
              {lastAssistant.citations.map((c, i) => (
                <li key={i} className="text-sm">
                  <button
                    onClick={() => openDocumentInNewTab(c.document_id)}
                    className="font-medium text-[var(--color-accent)] hover:underline text-left"
                  >
                    {c.document_name}
                  </button>
                  <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{c.snippet}</p>
                </li>
              ))}
            </ul>
          )}
        </aside>
      )}
    </div>
  );
}
