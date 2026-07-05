import { useEnvironment } from "../context/EnvironmentContext";

function FlagsPage() {
  const { environment } = useEnvironment();
  return (
    <h2 style={{ lineHeight: "1.4" }}>
      Flags Page — currently viewing: <span style={{ textTransform: "capitalize" }}>{environment}</span>
    </h2>
  );
}
export default FlagsPage;