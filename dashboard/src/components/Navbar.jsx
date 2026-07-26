import { useEnvironment } from "../context/EnvironmentContext";
import { capitalize } from "../utils/format";
import Dropdown from "./Dropdown";

function Navbar() {
  const { environments, environmentId, setEnvironmentId, environmentsLoading } = useEnvironment();
  const options = environments.map((e) => ({ value: e.id, label: capitalize(e.name) }));

  return (
    <div>
      <div className="flex justify-between items-center px-6 py-4 bg-white">
        <div>
          <h1 className="text-sm font-semibold text-gray-800">
            Application Feature Planning &amp; Release Governance System
          </h1>
          <p className="text-[11px] text-gray-400">Feature Flag Management Dashboard</p>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-gray-500 text-sm">Environment:</label>
          <Dropdown
            variant="pill"
            value={environmentId}
            options={options}
            onChange={setEnvironmentId}
            placeholder={environmentsLoading ? "Loading..." : "Select environment..."}
            disabled={environmentsLoading || options.length === 0}
          />
        </div>
      </div>
      <div className="h-[3px] w-full brand-gradient"></div>
    </div>
  );
}

export default Navbar;