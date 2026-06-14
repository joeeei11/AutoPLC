import type { Brand, ChatMessage, IOSignal, LLM } from "../api";
import { ChatTab } from "./ChatTab";
import { GenerateTab } from "./GenerateTab";
import { IOTableTab } from "./IOTableTab";

export type LeftTab = "generate" | "chat" | "iotable";

interface Props {
  activeTab: LeftTab;
  onTabChange: (tab: LeftTab) => void;
  description: string;
  brand: Brand;
  llm: LLM;
  stCode: string;
  loading: boolean;
  error: string | null;
  ioSignals: IOSignal[];
  chatMessages: ChatMessage[];
  onDescriptionChange: (v: string) => void;
  onBrandChange: (v: Brand) => void;
  onLLMChange: (v: LLM) => void;
  onGenerate: () => void;
  onDemoLoad: (index: number) => void;
  onFillDescription: (summary: string) => void;
  onIOSignalsChange: (signals: IOSignal[]) => void;
  onSwitchToIOTable: () => void;
  onChatMessagesChange: (messages: ChatMessage[]) => void;
}

export function LeftPanel({
  activeTab,
  onTabChange,
  description,
  brand,
  llm,
  stCode,
  loading,
  error,
  ioSignals,
  chatMessages,
  onDescriptionChange,
  onBrandChange,
  onLLMChange,
  onGenerate,
  onDemoLoad,
  onFillDescription,
  onIOSignalsChange,
  onSwitchToIOTable,
  onChatMessagesChange,
}: Props) {
  return (
    <aside className="left-panel">
      <div className="left-tabs" role="tablist">
        <button
          className={`left-tab${activeTab === "generate" ? " left-tab--active" : ""}`}
          role="tab"
          aria-selected={activeTab === "generate"}
          onClick={() => onTabChange("generate")}
        >
          生成
        </button>
        <button
          className={`left-tab${activeTab === "chat" ? " left-tab--active" : ""}`}
          role="tab"
          aria-selected={activeTab === "chat"}
          onClick={() => onTabChange("chat")}
        >
          对话
        </button>
        <button
          className={`left-tab${activeTab === "iotable" ? " left-tab--active" : ""}`}
          role="tab"
          aria-selected={activeTab === "iotable"}
          onClick={() => onTabChange("iotable")}
        >
          I/O 表
          {ioSignals.length > 0 && (
            <span className="tab-badge" aria-label={`${ioSignals.length} 条信号`}>
              {ioSignals.length}
            </span>
          )}
        </button>
      </div>

      <div className={`left-panel-content${activeTab === "generate" ? "" : " left-panel-content--hidden"}`}>
        <GenerateTab
          description={description}
          brand={brand}
          llm={llm}
          loading={loading}
          error={error}
          onDescriptionChange={onDescriptionChange}
          onBrandChange={onBrandChange}
          onLLMChange={onLLMChange}
          onGenerate={onGenerate}
          onDemoLoad={onDemoLoad}
        />
      </div>

      <div className={`left-panel-chat-area${activeTab === "chat" ? "" : " left-panel-chat-area--hidden"}`}>
        <ChatTab
          llm={llm}
          description={description}
          stCode={stCode}
          ioSignals={ioSignals}
          onFillDescription={onFillDescription}
          onIOSignalsChange={onIOSignalsChange}
          onSwitchToIOTable={onSwitchToIOTable}
          onMessagesChange={onChatMessagesChange}
        />
      </div>

      <div className={`left-panel-content${activeTab === "iotable" ? "" : " left-panel-content--hidden"}`}
           style={{ padding: 0, gap: 0 }}>
        <IOTableTab
          signals={ioSignals}
          llm={llm}
          chatMessages={chatMessages}
          onChange={onIOSignalsChange}
        />
      </div>
    </aside>
  );
}
