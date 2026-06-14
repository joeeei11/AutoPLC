import { useEffect, useState } from "react";
import { LeftPanel } from "./components/LeftPanel";
import type { LeftTab } from "./components/LeftPanel";
import { SvgPanel } from "./components/SvgPanel";
import { RightPanel } from "./components/RightPanel";
import {
  generatePLC,
  validatePLC,
  renderPLC,
  type Brand,
  type ChatMessage,
  type IOSignal,
  type LLM,
  type PLCProgram,
  type ValidationErrorItem,
} from "./api";
import { DEMO_SCENES } from "./demos";
import "./App.css";

type Theme = "dark" | "light";

export default function App() {
  const [theme, setTheme] = useState<Theme>("dark");
  const [description, setDescription] = useState("");
  const [brand, setBrand] = useState<Brand>("generic");
  const [llm, setLLM] = useState<LLM>("claude");
  const [leftTab, setLeftTab] = useState<LeftTab>("generate");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [plcProgram, setPlcProgram] = useState<PLCProgram | null>(null);
  const [svg, setSvg] = useState<string | null>(null);
  const [stCode, setStCode] = useState("");

  const [rerendering, setRerendering] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationErrorItem[]>([]);

  const [ioSignals, setIOSignals] = useState<IOSignal[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  async function handleGenerate() {
    if (!description.trim()) {
      setError("请输入控制逻辑描述（不能为空）");
      return;
    }

    setLoading(true);
    setError(null);
    setValidationErrors([]);

    try {
      const result = await generatePLC({ description, brand, llm, io_signals: ioSignals });
      setPlcProgram(result.plc_program);
      setSvg(result.svg);
      setStCode(result.plc_program.st_code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败，请重试");
    } finally {
      setLoading(false);
    }
  }

  async function handleRerender() {
    if (!plcProgram) return;

    const updated: PLCProgram = { ...plcProgram, st_code: stCode };

    setRerendering(true);
    setValidationErrors([]);

    try {
      const result = await validatePLC(updated);
      if (result.errors.length > 0) {
        setValidationErrors(result.errors);
      } else {
        const rendered = await renderPLC(updated);
        setSvg(rendered.svg);
        setPlcProgram(updated);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "重新渲染失败");
    } finally {
      setRerendering(false);
    }
  }

  async function handleDemoLoad(index: number) {
    const scene = DEMO_SCENES[index];
    if (!scene) return;
    setDescription(scene.description);
    setError(null);
    setValidationErrors([]);
    try {
      const { svg: demoSvg } = await renderPLC(scene.program);
      setPlcProgram(scene.program);
      setSvg(demoSvg);
      setStCode(scene.program.st_code);
    } catch {
      setError("Demo 加载失败，请确认后端已启动");
    }
  }

  function handleFillDescription(summary: string) {
    setDescription(summary);
    setLeftTab("generate");
  }

  return (
    <>
      <header className="app-topbar">
        <div className="app-brand">
          <span className="app-brand-mark" aria-hidden="true">⬡</span>
          <span className="app-brand-name">PLCLogicGen</span>
        </div>
        <button
          className="theme-toggle"
          onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
          aria-label={theme === "dark" ? "切换到亮色模式" : "切换到暗色模式"}
        >
          {theme === "dark" ? "☀ 亮色" : "◑ 暗色"}
        </button>
      </header>

      <div className="app-layout">
        <LeftPanel
          activeTab={leftTab}
          onTabChange={setLeftTab}
          description={description}
          brand={brand}
          llm={llm}
          stCode={stCode}
          loading={loading}
          error={error}
          ioSignals={ioSignals}
          chatMessages={chatMessages}
          onDescriptionChange={setDescription}
          onBrandChange={setBrand}
          onLLMChange={setLLM}
          onGenerate={handleGenerate}
          onDemoLoad={handleDemoLoad}
          onFillDescription={handleFillDescription}
          onIOSignalsChange={setIOSignals}
          onSwitchToIOTable={() => setLeftTab("iotable")}
          onChatMessagesChange={setChatMessages}
        />

        <SvgPanel svg={svg} />

        <RightPanel
          stCode={stCode}
          plcProgram={plcProgram}
          validationErrors={validationErrors}
          rerendering={rerendering}
          theme={theme}
          onChange={setStCode}
          onRerender={handleRerender}
        />
      </div>
    </>
  );
}
