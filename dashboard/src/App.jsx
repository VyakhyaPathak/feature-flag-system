import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import FlagsPage from "./pages/FlagsPage";
import EnvironmentsPage from "./pages/EnvironmentsPage";
import AuditLogPage from "./pages/AuditLogPage";

function App() {
  return (
    <BrowserRouter>
      <div style={{ display: "flex" }}>
        <Sidebar />
        <div style={{ flex: 1, padding: "20px" }}>
          <Routes>
            <Route path="/flags" element={<FlagsPage />} />
            <Route path="/environments" element={<EnvironmentsPage />} />
            <Route path="/audit-log" element={<AuditLogPage />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
export default App;