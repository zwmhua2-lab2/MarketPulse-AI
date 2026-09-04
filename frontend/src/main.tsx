import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  return <main><p className="eyebrow">MARKETPULSE AI · V1</p><h1>基础工程已就绪</h1><p>Group 1 市场数据与 Universe 服务正在建设中。</p></main>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);

