import { useEnvironment } from "../context/EnvironmentContext";

function Navbar() {
  const { environment, setEnvironment } = useEnvironment();

  return (
    <div className="flex justify-end items-center px-6 py-4 border-b border-gray-200 bg-white">
      <label className="text-gray-500 text-sm mr-3">Environment:</label>
      <select
        value={environment}
        onChange={(e) => setEnvironment(e.target.value)}
        className="bg-white text-gray-900 text-sm px-3 py-1.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        <option value="development">Development</option>
        <option value="staging">Staging</option>
        <option value="production">Production</option>
      </select>
    </div>
  );
}

export default Navbar;