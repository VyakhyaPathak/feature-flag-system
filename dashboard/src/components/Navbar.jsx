import { useEnvironment } from "../context/EnvironmentContext";

function Navbar() {
  const { environment, setEnvironment } = useEnvironment();

  return (
    <div style={{ padding: "15px 20px", borderBottom: "1px solid #ddd", display: "flex", justifyContent: "flex-end" }}>
      <label style={{ marginRight: "10px" }}>Environment:</label>
      <select value={environment} onChange={(e) => setEnvironment(e.target.value)}>
        <option value="development">Development</option>
        <option value="staging">Staging</option>
        <option value="production">Production</option>
      </select>
    </div>
  );
}

export default Navbar;