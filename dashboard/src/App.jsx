import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { EnvironmentProvider } from "./context/EnvironmentContext";
import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";
import FlagsPage from "./pages/FlagsPage";
import FlagDetailPage from "./pages/FlagDetailPage";
import EnvironmentsPage from "./pages/EnvironmentsPage";
import AuditLogPage from "./pages/AuditLogPage";

function App() {
  return (
    <EnvironmentProvider>
      <BrowserRouter>
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex-1">
            <Navbar />
            <Routes>
              <Route path="/" element={<Navigate to="/flags" replace />} />
              <Route path="/flags" element={<FlagsPage />} />
              <Route path="/flags/:flagId" element={<FlagDetailPage />} />
              <Route path="/environments" element={<EnvironmentsPage />} />
              <Route path="/audit-log" element={<AuditLogPage />} />
            </Routes>
          </div>
        </div>
      </BrowserRouter>
    </EnvironmentProvider>
  );
}

export default App;