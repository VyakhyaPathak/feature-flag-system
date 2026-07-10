import { Link, useLocation } from "react-router-dom";
import { Flag, Layers, ScrollText } from "lucide-react";

function Sidebar() {
  const location = useLocation();

  const navItems = [
    { to: "/flags", label: "Flags", icon: Flag },
    { to: "/environments", label: "Environments", icon: Layers },
    { to: "/audit-log", label: "Audit Log", icon: ScrollText },
  ];

  return (
    <div
      className="w-60 min-h-screen p-5 flex flex-col"
      style={{
        background:
          "linear-gradient(160deg, #33539E 0%, #A5678E 100%)",
      }}
    >
      <div className="flex items-center gap-3 mb-1 px-1">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 bg-white/20 backdrop-blur-sm">
          <Flag size={18} color="white" strokeWidth={2.5} />
        </div>
        <div>
          <h3 className="font-bold text-base text-white leading-tight">FlagCtrl</h3>
          <p className="text-[11px] text-white/70 leading-tight">Feature Flag Manager</p>
        </div>
      </div>

      <nav className="flex flex-col gap-1 mt-8">
        {navItems.map(({ to, label, icon: Icon }) => {
          const isActive = location.pathname.startsWith(to);
          return (
            <Link
              key={to}
              to={to}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition ${
                isActive
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-white/85 hover:bg-white/15"
              }`}
            >
              <Icon size={16} strokeWidth={2} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto pt-6 border-t border-white/20">
        <p className="text-[11px] text-white/60 px-1">v0.1.0 — Milestone 1</p>
      </div>
    </div>
  );
}

export default Sidebar;