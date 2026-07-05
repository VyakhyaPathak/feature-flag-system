import { BrowserRouter, Routes, Route } from "react-router-dom";
import { EnvironmentProvider } from "./context/EnvironmentContext";
import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";
import FlagsPage from "./pages/FlagsPage";
import EnvironmentsPage from "./pages/EnvironmentsPage";
import AuditLogPage from "./pages/AuditLogPage";

function App() {
  return (
    <EnvironmentProvider>
      <BrowserRouter>
        <div style={{ display: "flex" }}>
          <Sidebar />
          <div style={{ flex: 1 }}>
            <Navbar />
            <div style={{ padding: "20px" }}>
              <Routes>
                <Route path="/flags" element={<FlagsPage />} />
                <Route path="/environments" element={<EnvironmentsPage />} />
                <Route path="/audit-log" element={<AuditLogPage />} />
              </Routes>
            </div>
          </div>
        </div>
      </BrowserRouter>
    </EnvironmentProvider>
  );
}

export default App;