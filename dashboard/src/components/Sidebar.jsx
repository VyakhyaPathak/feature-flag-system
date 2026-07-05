import { Link } from "react-router-dom";

function Sidebar() {
  return (
    <div className="w-56 bg-white border-r border-gray-200 min-h-screen p-5">
      <h3 className="text-gray-900 font-bold text-lg mb-8">FlagCtrl</h3>
      <nav className="flex flex-col gap-1">
        <Link to="/flags" className="text-gray-600 hover:bg-gray-100 hover:text-gray-900 px-3 py-2 rounded-lg text-sm transition">
          Flags
        </Link>
        <Link to="/environments" className="text-gray-600 hover:bg-gray-100 hover:text-gray-900 px-3 py-2 rounded-lg text-sm transition">
          Environments
        </Link>
        <Link to="/audit-log" className="text-gray-600 hover:bg-gray-100 hover:text-gray-900 px-3 py-2 rounded-lg text-sm transition">
          Audit Log
        </Link>
      </nav>
    </div>
  );
}

export default Sidebar;