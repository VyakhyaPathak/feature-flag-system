import { useState, useRef, useEffect } from "react";
import { ChevronDown, Check } from "lucide-react";

// variant="field" -> plain bordered box, full width (used in forms)
// variant="pill"  -> compact gradient button, fixed-width panel (used in Navbar)
function Dropdown({
  value,
  options,
  onChange,
  disabled = false,
  placeholder = "Select...",
  variant = "field",
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selected = options.find((o) => o.value === value);

  const optionsList = (panelClassName) => (
    <div className={panelClassName}>
      {options.map((opt) => {
        const isSelected = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => {
              onChange(opt.value);
              setOpen(false);
            }}
            className="w-full flex items-center justify-between px-3 py-2 text-sm text-left transition"
            style={{
              color: isSelected ? "#33539E" : "#374151",
              backgroundColor: isSelected ? "rgba(51,83,158,0.08)" : "transparent",
            }}
            onMouseEnter={(e) => {
              if (!isSelected) e.currentTarget.style.backgroundColor = "rgba(51,83,158,0.05)";
            }}
            onMouseLeave={(e) => {
              if (!isSelected) e.currentTarget.style.backgroundColor = "transparent";
            }}
          >
            {opt.label}
            {isSelected && <Check size={14} style={{ color: "#33539E" }} />}
          </button>
        );
      })}
    </div>
  );

  if (variant === "pill") {
    return (
      <div className="relative" ref={ref}>
        <button
          type="button"
          onClick={() => !disabled && setOpen(!open)}
          className="flex items-center gap-2 text-white text-sm font-medium pl-3 pr-2.5 py-1.5 rounded-lg focus:outline-none cursor-pointer"
          style={{ background: "linear-gradient(160deg, #33539E, #A5678E)" }}
        >
          {selected ? selected.label : placeholder}
          <ChevronDown size={14} className={`transition-transform ${open ? "rotate-180" : ""}`} />
        </button>

        {open &&
          optionsList(
            "absolute right-0 mt-1.5 w-40 bg-white rounded-lg shadow-lg border border-gray-100 overflow-hidden z-50"
          )}
      </div>
    );
  }

  return (
    <div className="relative w-full" ref={ref}>
      <button
        type="button"
        onClick={() => !disabled && setOpen(!open)}
        disabled={disabled}
        className="w-full flex items-center justify-between border border-gray-300 rounded-lg px-3 py-2 text-sm text-left focus:outline-none disabled:bg-gray-100 disabled:text-gray-500"
      >
        <span className={selected ? "text-gray-900" : "text-gray-400"}>
          {selected ? selected.label : placeholder}
        </span>
        <ChevronDown
          size={14}
          className={`text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open &&
        !disabled &&
        optionsList(
          "absolute top-full left-0 w-full mt-1.5 bg-white rounded-lg shadow-lg border border-gray-100 overflow-hidden z-50"
        )}
    </div>
  );
}

export default Dropdown;