import { useEffect, useRef, useState } from "react";
import type { ChatMessage, IOSignal, LLM } from "../api";
import { generateIOTable, streamChat, streamFDS } from "../api";

const SUMMARY_START = "---SUMMARY---";
const SUMMARY_END = "---END---";

function parseSummary(text: string): { body: string; summary: string | null } {
  const startIdx = text.indexOf(SUMMARY_START);
  const endIdx = text.indexOf(SUMMARY_END);
  if (startIdx === -1 || endIdx === -1 || endIdx < startIdx) {
    return { body: text, summary: null };
  }
  const summary = text.slice(startIdx + SUMMARY_START.length, endIdx).trim();
  const body = (text.slice(0, startIdx) + text.slice(endIdx + SUMMARY_END.length)).trim();
  return { body, summary };
}

function renderInlineText(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`\n]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={i} className="chat-inline-code">{part.slice(1, -1)}</code>;
    }
    return <span key={i} style={{ whiteSpace: "pre-wrap" }}>{part}</span>;
  });
}

function renderMarkdown(text: string): React.ReactNode[] {
  const segments = text.split(/(```[\s\S]*?```)/g);
  return segments.map((seg, i) => {
    if (seg.startsWith("```")) {
      const newline = seg.indexOf("\n");
      const code = newline === -1 ? seg.slice(3, -3) : seg.slice(newline + 1, -3);
      return (
        <pre key={i} className="chat-code-block">
          <code>{code}</code>
        </pre>
      );
    }
    return <span key={i}>{renderInlineText(seg)}</span>;
  });
}

interface Message {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

interface Props {
  llm: LLM;
  description: string;
  stCode: string;
  ioSignals: IOSignal[];
  onFillDescription: (summary: string) => void;
  onIOSignalsChange: (signals: IOSignal[]) => void;
  onSwitchToIOTable: () => void;
  onMessagesChange?: (messages: ChatMessage[]) => void;
}

export function ChatTab({ llm, description, stCode, ioSignals, onFillDescription, onIOSignalsChange, onSwitchToIOTable, onMessagesChange }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatingIO, setGeneratingIO] = useState(false);
  const [fdsText, setFdsText] = useState("");
  const [streamingFDS, setStreamingFDS] = useState(false);
  const [fdsCopied, setFdsCopied] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const listEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, fdsText]);

  const apiMessages: ChatMessage[] = messages
    .filter((m) => !m.streaming)
    .map((m) => ({ role: m.role, content: m.content }));

  async function handleSend() {
    const text = input.trim();
    if (!text || streaming) return;

    const outgoing: ChatMessage[] = [...apiMessages, { role: "user", content: text }];

    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: "", streaming: true },
    ]);
    setInput("");
    setStreaming(true);
    setError(null);

    const controller = new AbortController();
    abortRef.current = controller;
    let accumulated = "";

    try {
      await streamChat(
        { messages: outgoing, description, st_code: stCode, llm },
        (chunk) => {
          accumulated += chunk;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = { role: "assistant", content: accumulated, streaming: true };
            return updated;
          });
        },
        controller.signal
      );

      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", content: accumulated, streaming: false };
        onMessagesChange?.(updated.filter((m) => !m.streaming).map((m) => ({ role: m.role, content: m.content })));
        return updated;
      });
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        if (accumulated) {
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = { role: "assistant", content: accumulated, streaming: false };
            onMessagesChange?.(updated.map((m) => ({ role: m.role, content: m.content })));
            return updated;
          });
        } else {
          setMessages((prev) => prev.slice(0, -2));
        }
      } else {
        setError(err instanceof Error ? err.message : "对话请求失败，请重试");
        setMessages((prev) => prev.slice(0, -2));
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }

  async function handleGenerateIO() {
    if (apiMessages.length === 0) {
      setError("请先完成需求对话");
      return;
    }
    setGeneratingIO(true);
    setError(null);
    try {
      const signals = await generateIOTable(apiMessages, llm);
      onIOSignalsChange(signals);
      onSwitchToIOTable();
    } catch (err) {
      setError(err instanceof Error ? err.message : "I/O 表生成失败");
    } finally {
      setGeneratingIO(false);
    }
  }

  async function handleGenerateFDS() {
    if (apiMessages.length === 0) {
      setError("请先完成需求对话");
      return;
    }
    setStreamingFDS(true);
    setFdsText("");
    setError(null);
    const controller = new AbortController();
    abortRef.current = controller;
    let accumulated = "";
    try {
      await streamFDS(
        apiMessages,
        ioSignals,
        llm,
        (chunk) => {
          accumulated += chunk;
          setFdsText(accumulated);
        },
        controller.signal
      );
    } catch (err) {
      if (!(err instanceof Error && err.name === "AbortError")) {
        setError(err instanceof Error ? err.message : "FDS 生成失败");
      }
    } finally {
      setStreamingFDS(false);
      abortRef.current = null;
    }
  }

  async function handleCopyFDS() {
    await navigator.clipboard.writeText(fdsText);
    setFdsCopied(true);
    setTimeout(() => setFdsCopied(false), 2000);
  }

  function handleDownloadFDS() {
    const blob = new Blob([fdsText], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "FDS.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleCancel() {
    abortRef.current?.abort();
  }

  function handleClear() {
    setMessages([]);
    setFdsText("");
    setError(null);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const hasConversation = apiMessages.length > 0;

  return (
    <div className="chat-tab">
      <div className="chat-messages" role="log" aria-live="polite">
        {messages.length === 0 && (
          <div className="chat-empty">
            发送消息开始与资深 PLC 工程师 AI 对话，帮助您梳理控制逻辑需求。
          </div>
        )}
        {messages.map((msg, i) => {
          if (msg.role === "user") {
            return (
              <div key={i} className="chat-bubble chat-bubble--user">
                {msg.content}
              </div>
            );
          }
          const { body, summary } = parseSummary(msg.content);
          return (
            <div key={i} className="chat-bubble chat-bubble--assistant">
              {renderMarkdown(body)}
              {msg.streaming && (
                <span className="chat-cursor" aria-hidden="true">▍</span>
              )}
              {!msg.streaming && summary && (
                <div className="chat-summary-card">
                  <div className="chat-summary-label">当前需求摘要</div>
                  <div className="chat-summary-body">{summary}</div>
                  <button className="chat-fill-btn" onClick={() => onFillDescription(summary)}>
                    填入描述并生成
                  </button>
                </div>
              )}
            </div>
          );
        })}

        {hasConversation && (
          <div className="chat-action-cards">
            <div className="chat-action-card">
              <div className="chat-action-card-title">I/O 分配表</div>
              <div className="chat-action-card-desc">从对话中提取信号，生成 I/O 表初稿</div>
              <button
                className="chat-action-btn"
                onClick={handleGenerateIO}
                disabled={generatingIO || streaming}
                aria-label="生成 I/O 表"
              >
                {generatingIO ? "提取中…" : "生成 I/O 表"}
              </button>
            </div>
            <div className="chat-action-card">
              <div className="chat-action-card-title">功能规格说明书</div>
              <div className="chat-action-card-desc">根据对话和 I/O 表生成 FDS 文档</div>
              <button
                className="chat-action-btn"
                onClick={streamingFDS ? handleCancel : handleGenerateFDS}
                disabled={streaming}
                aria-label={streamingFDS ? "停止生成 FDS" : "生成 FDS"}
              >
                {streamingFDS ? "停止" : "生成 FDS"}
              </button>
            </div>
          </div>
        )}

        {(fdsText || streamingFDS) && (
          <div className="chat-fds-card">
            <div className="chat-fds-header">
              <span className="chat-fds-title">功能规格说明书（FDS）</span>
              <div className="chat-fds-btns">
                <button
                  className="chat-fds-btn"
                  onClick={handleCopyFDS}
                  disabled={!fdsText}
                  aria-label="复制 FDS 内容"
                >
                  {fdsCopied ? "已复制" : "复制"}
                </button>
                <button
                  className="chat-fds-btn"
                  onClick={handleDownloadFDS}
                  disabled={!fdsText}
                  aria-label="下载 FDS 为 Markdown"
                >
                  下载 .md
                </button>
              </div>
            </div>
            <div className="chat-fds-body">
              {renderMarkdown(fdsText)}
              {streamingFDS && <span className="chat-cursor" aria-hidden="true">▍</span>}
            </div>
          </div>
        )}

        <div ref={listEndRef} />
      </div>

      {error && (
        <div className="error-box chat-error" role="alert">
          <strong>错误：</strong>
          <span>{error}</span>
        </div>
      )}

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入消息… (Enter 发送，Shift+Enter 换行)"
          rows={3}
          disabled={streaming}
          aria-label="对话输入框"
        />
        <div className="chat-actions">
          {streaming ? (
            <button className="chat-cancel-btn" onClick={handleCancel} aria-label="停止生成">
              停止
            </button>
          ) : (
            <button
              className="chat-send-btn"
              onClick={handleSend}
              disabled={!input.trim()}
              aria-label="发送"
            >
              发送
            </button>
          )}
          <button
            className="chat-clear-btn"
            onClick={handleClear}
            disabled={streaming}
            aria-label="清空对话"
          >
            清空
          </button>
        </div>
      </div>
    </div>
  );
}
