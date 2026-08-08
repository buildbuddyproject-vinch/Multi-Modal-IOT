import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import AlertToastStack from "./AlertToastStack";

export default function AppLayout() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main-col">
        <Outlet />
      </div>
      <AlertToastStack />
    </div>
  );
}
