import { useEnvironment } from "../context/EnvironmentContext";

function AuditLogPage() {
  const { environment } = useEnvironment();
  return <h2>Audit Log Page — currently viewing: {environment}</h2>;
}
export default AuditLogPage;