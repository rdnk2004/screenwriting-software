import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ScriptList from "./pages/ScriptList.jsx";
import ScriptEditor from "./pages/ScriptEditor.jsx";
import ScriptCharacters from "./pages/ScriptCharacters.jsx";
import ScriptDiagram from "./pages/ScriptDiagram.jsx";
import ScriptOutline from "./pages/ScriptOutline.jsx";
import ScriptAnalysis from "./pages/ScriptAnalysis.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ScriptList />} />
        <Route path="/scripts/:id" element={<ScriptEditor />} />
        <Route path="/scripts/:id/characters" element={<ScriptCharacters />} />
        <Route path="/scripts/:id/diagram" element={<ScriptDiagram />} />
        <Route path="/scripts/:id/outline" element={<ScriptOutline />} />
        <Route path="/scripts/:id/analysis" element={<ScriptAnalysis />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
