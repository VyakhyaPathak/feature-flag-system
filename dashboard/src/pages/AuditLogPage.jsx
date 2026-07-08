import { ScrollText } from "lucide-react";

function AuditLogPage() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-semibold brand-gradient-text mb-6">Audit Log</h2>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 flex flex-col items-center text-center">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center mb-4"
          style={{ background: "linear-gradient(135deg, rgba(51,83,158,0.1), rgba(165,103,142,0.1))" }}
        >
          <ScrollText size={22} style={{ color: "#33539E" }} />
        </div>
        <p className="text-gray-500 text-sm">
          Audit logging will track every flag change here — coming in Day 15.
        </p>
      </div>
    </div>
  );
}

export default AuditLogPage;