import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ScriptList from "./pages/ScriptList.jsx";
import ScriptEditor from "./pages/ScriptEditor.jsx";
import ScriptCharacters from "./pages/ScriptCharacters.jsx";
import ScriptDiagram from "./pages/ScriptDiagram.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ScriptList />} />
        <Route path="/scripts/:id" element={<ScriptEditor />} />
        <Route path="/scripts/:id/characters" element={<ScriptCharacters />} />
        <Route path="/scripts/:id/diagram" element={<ScriptDiagram />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
