import { useEnvironment } from "../context/EnvironmentContext";

function Navbar() {
  const { environment, setEnvironment } = useEnvironment();

  return (
    <div>
      <div className="flex justify-end items-center px-6 py-4 bg-white">
        <label className="text-gray-500 text-sm mr-3">Environment:</label>
        <select
          value={environment}
          onChange={(e) => setEnvironment(e.target.value)}
          className="bg-white text-gray-900 text-sm px-3 py-1.5 rounded-lg border focus:outline-none"
          style={{ borderColor: "#BFB8DA" }}
          onFocus={(e) => (e.target.style.boxShadow = "0 0 0 2px rgba(51,83,158,0.25)")}
          onBlur={(e) => (e.target.style.boxShadow = "none")}
        >
          <option value="development">Development</option>
          <option value="staging">Staging</option>
          <option value="production">Production</option>
        </select>
      </div>
      <div className="h-[3px] w-full brand-gradient"></div>
    </div>
  );
}

export default Navbar;