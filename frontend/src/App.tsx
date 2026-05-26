import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Overview } from "./pages/Overview";
import { EngineDetail } from "./pages/EngineDetail";
import { Agents } from "./pages/Agents";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Overview />} />
          <Route path="/engine/:id" element={<EngineDetail />} />
          <Route path="/agents" element={<Agents />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
