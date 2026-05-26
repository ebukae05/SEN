import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Overview } from "./pages/Overview";
import { EngineDetail } from "./pages/EngineDetail";
import { Agents } from "./pages/Agents";
import { Recommendations } from "./pages/Recommendations";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/fleet" replace />} />
          <Route path="/fleet" element={<Overview />} />
          <Route path="/engine/:id" element={<EngineDetail />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/recommendations" element={<Recommendations />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
