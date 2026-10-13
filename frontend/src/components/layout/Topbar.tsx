import React from "react";
import { Menu, ChevronRight, Shield } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

interface TopbarProps {
  title?: string;
  breadcrumb?: string[];
  onOpenSidebar: () => void;
  activeBatchName?: string;
}

export const Topbar: React.FC<TopbarProps> = ({
  title = "Dashboard Adjudikasi",
  breadcrumb = ["Tata Kelola", "Tahap I 2026"],
  onOpenSidebar,
  activeBatchName = "Tahap I 2026",
}) => {
  const { user } = useAuth();

  const getRoleBadge = () => {
    switch (user?.role) {
      case "SUPER_ADMIN":
        return { label: "Kasi Kesos", bg: "bg-emerald-50 text-emerald-800 border-emerald-200" };
      case "VIEWER":
        return { label: "Lurah", bg: "bg-blue-50 text-blue-800 border-blue-200" };
      case "SURVEYOR":
        return {
          label: `Ketua RT ${user.rt_number || ""}`,
          bg: "bg-amber-50 text-amber-800 border-amber-200",
        };
      default:
        return { label: "Staf", bg: "bg-gray-50 text-gray-800 border-gray-200" };
    }
  };

  const badge = getRoleBadge();

  return (
    <header className="sticky top-0 z-20 bg-white border-b border-border-subtle shadow-sm transition-all">
      <div className="flex items-center justify-between px-4 sm:px-6 py-2.5 gap-2">
        {/* Left: Mobile Menu Button + Title / Breadcrumbs */}
        <div className="flex items-center gap-3 min-w-0">
          {/* Hamburger button for mobile/tablet */}
          <button
            type="button"
            aria-label="Buka menu navigasi"
            onClick={onOpenSidebar}
            className="lg:hidden p-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-subtle transition-colors shrink-0"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Breadcrumb & Title */}
          <div className="flex flex-col min-w-0">
            <nav aria-label="Breadcrumb" className="hidden sm:flex items-center gap-1.5 text-[11px] font-mono text-on-surface-variant/80">
              <span className="text-primary font-semibold">EDSS JUBAR</span>
              {breadcrumb.map((crumb, idx) => (
                <React.Fragment key={idx}>
                  <ChevronRight className="w-3 h-3 text-outline/50 shrink-0" />
                  <span className={idx === breadcrumb.length - 1 ? "text-on-surface font-medium truncate" : "truncate"}>
                    {crumb}
                  </span>
                </React.Fragment>
              ))}
            </nav>
            <h1 className="text-base sm:text-lg font-bold text-on-surface tracking-tight truncate leading-tight">
              {title}
            </h1>
          </div>
        </div>

        {/* Right: Batch Switcher, Worker Pulse & User Badge */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {/* Active Batch Indicator */}
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-subtle border border-border-subtle text-xs font-mono text-on-surface">
            <span className="w-1.5 h-1.5 rounded-full bg-primary" />
            <span className="font-semibold">{activeBatchName}</span>
          </div>

          {/* Celery Worker Heartbeat */}
          <div
            title="Sistem Antrean Pemrosesan XAI Siap"
            className="flex items-center gap-1.5 px-2 py-1 rounded bg-status-approved-bg border border-emerald-200/60 text-status-approved-fg text-[11px] font-mono"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600" />
            </span>
            <span className="hidden sm:inline">Worker Siap</span>
          </div>

          {/* Role Badge */}
          <div
            className={`flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium border ${badge.bg}`}
          >
            <Shield className="w-3 h-3 shrink-0" />
            <span>{badge.label}</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Topbar;
