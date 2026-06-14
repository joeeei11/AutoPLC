import { useState } from "react";
import { LeftPanel } from "./components/LeftPanel";
import { SvgPanel } from "./components/SvgPanel";
import { RightPanel } from "./components/RightPanel";
import {
  generatePLC,
  validatePLC,
  renderPLC,
  type Brand,
  type LLM,
  type PLCProgram,
  type ValidationErrorItem,
} from "./api";
import { DEMO_SCENES } from "./demos";
import "./App.css";

export default function App() {
  const [description, setDescription] = useState("");
  const [brand, setBrand] = useState<Brand>("generic");
  const [llm, setLLM] = useState<LLM>("claude");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [plcProgram, setPlcProgram] = useState<PLCProgram | null>(null);
  const [svg, setSvg] = useState<string | null>(null);
  const [stCode, setStCode] = useState("");

  const [rerendering, setRerendering] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationErrorItem[]>([]);

  async function handleGenerate() {
    if (!description.trim()) {
      setError("请输入控制逻辑描述（不能为空）");
      return;
    }

    setLoading(true);
    setError(null);
    setValidationErrors([]);

    try {
      const result = await generatePLC({ description, brand, llm });
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
        const gen = await generatePLC({ description, brand, llm });
        setSvg(gen.svg);
        setPlcProgram(gen.plc_program);
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

  return (
    <div className="app-layout">
      <LeftPanel
        description={description}
        brand={brand}
        llm={llm}
        loading={loading}
        error={error}
        onDescriptionChange={setDescription}
        onBrandChange={setBrand}
        onLLMChange={setLLM}
        onGenerate={handleGenerate}
        onDemoLoad={handleDemoLoad}
      />

      <SvgPanel svg={svg} />

      <RightPanel
        stCode={stCode}
        plcProgram={plcProgram}
        validationErrors={validationErrors}
        rerendering={rerendering}
        onChange={setStCode}
        onRerender={handleRerender}
      />
    </div>
  );
}
