import { Link } from "react-router-dom";

function Sidebar() {
  return (
    <div style={{ width: "200px", padding: "20px" }}>
      <h3>FlagCtrl</h3>
      <ul>
        <li><Link to="/flags">Flags</Link></li>
        <li><Link to="/environments">Environments</Link></li>
        <li><Link to="/audit-log">Audit Log</Link></li>
      </ul>
    </div>
  );
}
export default Sidebar;