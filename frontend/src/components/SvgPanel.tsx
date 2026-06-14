import { useRef, useState } from "react";
import type { WheelEvent as ReactWheelEvent } from "react";

interface Props {
  svg: string | null;
}

export function SvgPanel({ svg }: Props) {
  const [scale, setScale] = useState(1);
  const containerRef = useRef<HTMLDivElement>(null);

  function handleWheel(e: ReactWheelEvent<HTMLDivElement>) {
    e.preventDefault();
    setScale((s) => Math.min(4, Math.max(0.2, s - e.deltaY * 0.001)));
  }

  return (
    <section className="svg-panel" aria-label="梯形图预览">
      {svg ? (
        <div
          ref={containerRef}
          className="svg-scroll"
          onWheel={handleWheel}
        >
          <div
            className="svg-inner"
            style={{ transform: `scale(${scale})`, transformOrigin: "top left" }}
            // 直接注入 SVG 字符串，后端生成的 SVG 是可信内部数据
            dangerouslySetInnerHTML={{ __html: svg }}
          />
        </div>
      ) : (
        <div className="svg-placeholder">生成后梯形图将显示在此处</div>
      )}

      {svg && (
        <div className="zoom-controls">
          <button onClick={() => setScale((s) => Math.min(4, s + 0.1))}>＋</button>
          <span>{Math.round(scale * 100)}%</span>
          <button onClick={() => setScale((s) => Math.max(0.2, s - 0.1))}>－</button>
          <button onClick={() => setScale(1)}>重置</button>
        </div>
      )}
    </section>
  );
}
