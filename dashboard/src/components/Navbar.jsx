import { useState, useRef, useEffect } from "react";
import { useEnvironment } from "../context/EnvironmentContext";
import { ChevronDown, Check } from "lucide-react";

const options = [
  { value: "development", label: "Development" },
  { value: "staging", label: "Staging" },
  { value: "production", label: "Production" },
];

function Navbar() {
  const { environment, setEnvironment } = useEnvironment();
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const currentLabel = options.find((o) => o.value === environment)?.label;

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
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setOpen(!open)}
              className="flex items-center gap-2 text-white text-sm font-medium pl-3 pr-2.5 py-1.5 rounded-lg focus:outline-none cursor-pointer"
              style={{ background: "linear-gradient(160deg, #33539E, #A5678E)" }}
            >
              {currentLabel}
              <ChevronDown
                size={14}
                className={`transition-transform ${open ? "rotate-180" : ""}`}
              />
            </button>

            {open && (
              <div className="absolute right-0 mt-1.5 w-40 bg-white rounded-lg shadow-lg border border-gray-100 overflow-hidden z-50">
                {options.map((opt) => {
                  const isSelected = opt.value === environment;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => {
                        setEnvironment(opt.value);
                        setOpen(false);
                      }}
                      className="w-full flex items-center justify-between px-3 py-2 text-sm text-left transition"
                      style={{
                        color: isSelected ? "#33539E" : "#374151",
                        backgroundColor: isSelected ? "rgba(51,83,158,0.08)" : "transparent",
                      }}
                      onMouseEnter={(e) => {
                        if (!isSelected) e.target.style.backgroundColor = "rgba(51,83,158,0.05)";
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) e.target.style.backgroundColor = "transparent";
                      }}
                    >
                      {opt.label}
                      {isSelected && <Check size={14} style={{ color: "#33539E" }} />}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="h-[3px] w-full brand-gradient"></div>
    </div>
  );
}

export default Navbar;