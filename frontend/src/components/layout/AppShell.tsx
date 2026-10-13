import React, { useState } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export interface AppShellProps {
  title: string;
  breadcrumb?: string[];
  children: React.ReactNode;
  onExecuteSaw?: () => void;
  activeBatchName?: string;
}

export const AppShell: React.FC<AppShellProps> = ({
  title,
  breadcrumb = ["Tata Kelola"],
  children,
  onExecuteSaw,
  activeBatchName = "Tahap I 2026",
}) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const openSidebar = () => setIsSidebarOpen(true);
  const closeSidebar = () => setIsSidebarOpen(false);

  return (
    <div className="min-h-screen bg-surface-canvas text-on-surface flex flex-col font-sans">
      {/* Persistent / Responsive Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={closeSidebar}
        onExecuteSaw={onExecuteSaw}
      />

      {/* Main Content Area: Offset by lg:pl-64 on desktop */}
      <div className="flex-1 flex flex-col lg:pl-64 transition-all">
        {/* Top Docked Navigation */}
        <Topbar
          title={title}
          breadcrumb={breadcrumb}
          onOpenSidebar={openSidebar}
          activeBatchName={activeBatchName}
        />

        {/* Dynamic Page Content */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 w-full max-w-7xl mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

export default AppShell;
