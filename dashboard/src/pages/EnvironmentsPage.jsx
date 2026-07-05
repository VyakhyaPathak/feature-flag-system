import { useEnvironment } from "../context/EnvironmentContext";

function EnvironmentsPage() {
  const { environment } = useEnvironment();
  return <h2>Environments Page — currently viewing: {environment}</h2>;
}
export default EnvironmentsPage;