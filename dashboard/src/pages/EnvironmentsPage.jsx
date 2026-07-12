import { Layers } from "lucide-react";
import { ENVIRONMENTS } from "../constants/environments";

function EnvironmentsPage() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-semibold brand-gradient-text mb-6">Environments</h2>

      <div className="grid grid-cols-3 gap-4">
        {ENVIRONMENTS.map((env) => (
          <div
            key={env.id}
            className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
          >
            <div className="h-1.5" style={{ backgroundColor: env.color }}></div>
            <div className="p-5 flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center"
                style={{ backgroundColor: `${env.color}15` }}
              >
                <Layers size={18} style={{ color: env.color }} />
              </div>
              <div>
                <p className="font-semibold text-gray-900">{env.label}</p>
                <p className="text-xs text-gray-400">ID: {env.id}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <p className="text-gray-400 text-sm italic mt-6">
        Environment-specific flag overrides coming in Day 10.
      </p>
    </div>
  );
}

export default EnvironmentsPage;