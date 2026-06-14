import type { Brand, LLM } from "../api";
import { DEMO_SCENES } from "../demos";

interface Props {
  description: string;
  brand: Brand;
  llm: LLM;
  loading: boolean;
  error: string | null;
  onDescriptionChange: (v: string) => void;
  onBrandChange: (v: Brand) => void;
  onLLMChange: (v: LLM) => void;
  onGenerate: () => void;
  onDemoLoad: (index: number) => void;
}

export function GenerateTab({
  description,
  brand,
  llm,
  loading,
  error,
  onDescriptionChange,
  onBrandChange,
  onLLMChange,
  onGenerate,
  onDemoLoad,
}: Props) {
  return (
    <>
      <div className="demo-section">
        <span className="field-label">Demo 场景</span>
        <div className="demo-buttons" role="group" aria-label="Demo 场景">
          {DEMO_SCENES.map((scene, i) => (
            <button
              key={i}
              className="demo-btn"
              onClick={() => onDemoLoad(i)}
              title={scene.description}
              aria-label={`加载 Demo：${scene.label}`}
            >
              {scene.label}
            </button>
          ))}
        </div>
      </div>

      <label className="field-label">控制逻辑描述</label>
      <textarea
        className="description-input"
        value={description}
        onChange={(e) => onDescriptionChange(e.target.value)}
        placeholder="例如：电机在温度超过 80°C 时停止，延时 5 秒后重启"
        rows={6}
      />

      <label className="field-label">目标品牌 / 格式</label>
      <select
        className="select"
        value={brand}
        onChange={(e) => onBrandChange(e.target.value as Brand)}
      >
        <option value="generic">通用 ST（IEC 61131-3）</option>
        <option value="siemens">西门子 SCL</option>
        <option value="rockwell">罗克韦尔 L5X</option>
      </select>

      <label className="field-label">语言模型</label>
      <select
        className="select"
        value={llm}
        onChange={(e) => onLLMChange(e.target.value as LLM)}
      >
        <option value="claude">Claude</option>
        <option value="openai">OpenAI</option>
      </select>

      <button
        className="generate-btn"
        onClick={onGenerate}
        disabled={loading}
      >
        {loading ? "生成中…" : "生成梯形图"}
      </button>

      {error && (
        <div className="error-box" role="alert">
          <strong>错误：</strong>
          <span>{error}</span>
        </div>
      )}
    </>
  );
}
