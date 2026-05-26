import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Overview } from "./pages/Overview";
import { EngineDetail } from "./pages/EngineDetail";
import { Agents } from "./pages/Agents";
import { Recommendations } from "./pages/Recommendations";
import { Alerts } from "./pages/Alerts";
import { Trends } from "./pages/Trends";
import { Diagnostics } from "./pages/Diagnostics";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/fleet" replace />} />
          <Route path="/fleet" element={<Overview />} />
          <Route path="/engine/:id" element={<EngineDetail />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/trends" element={<Trends />} />
          <Route path="/diagnostics" element={<Diagnostics />} />
          <Route path="/recommendations" element={<Recommendations />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
