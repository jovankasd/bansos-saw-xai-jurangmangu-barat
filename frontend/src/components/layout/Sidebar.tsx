import React, { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  ClipboardCheck,
  Brain,
  FileCheck,
  Sliders,
  GraduationCap,
  ShieldCheck,
  Zap,
  LogOut,
  X,
  FileText,
  HelpCircle,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { UserRole } from "../../types/auth";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: UserRole[];
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    name: "Dashboard Adjudikasi",
    href: "/admin/dashboard",
    icon: LayoutDashboard,
    roles: ["SUPER_ADMIN", "VIEWER"],
  },
  {
    name: "Dashboard RT",
    href: "/admin/dashboard",
    icon: LayoutDashboard,
    roles: ["SURVEYOR"],
  },
  {
    name: "Data Warga RT",
    href: "/admin/citizens",
    icon: Users,
    roles: ["SURVEYOR"],
  },
  {
    name: "Data Warga & Import RT",
    href: "/admin/citizens",
    icon: Users,
    roles: ["SUPER_ADMIN"],
  },
  {
    name: "Dossier & Seleksi SAW",
    href: "/admin/selection",
    icon: ClipboardCheck,
    roles: ["SUPER_ADMIN", "VIEWER"],
  },
  {
    name: "Status Usulan RT",
    href: "/admin/selection",
    icon: ClipboardCheck,
    roles: ["SURVEYOR"],
  },
  {
    name: "XAI Model Explainability",
    href: "/admin/xai",
    icon: Brain,
    roles: ["SUPER_ADMIN", "VIEWER"],
  },
  {
    name: "Pengesahan Berita Acara",
    href: "/admin/berita-acara",
    icon: FileCheck,
    roles: ["SUPER_ADMIN", "VIEWER"],
  },
  {
    name: "Konfigurasi Bobot SAW",
    href: "/admin/criteria",
    icon: Sliders,
    roles: ["SUPER_ADMIN"],
  },
  {
    name: "Evaluasi Skripsi",
    href: "/admin/evaluation",
    icon: GraduationCap,
    roles: ["SUPER_ADMIN"],
  },
  {
    name: "Audit Log & Integritas",
    href: "/admin/audit",
    icon: ShieldCheck,
    roles: ["SUPER_ADMIN", "VIEWER"],
  },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onExecuteSaw?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  onExecuteSaw,
}) => {
  const { user, logout } = useAuth();
  const location = useLocation();

  // Close drawer on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const userRole = user?.role || "VIEWER";
  const filteredNavItems = NAV_ITEMS.filter((item) => item.roles.includes(userRole));

  const getRoleTitle = (role: UserRole) => {
    switch (role) {
      case "SUPER_ADMIN":
        return "Kasi Kesos Kelurahan";
      case "VIEWER":
        return "Lurah Jurangmangu Barat";
      case "SURVEYOR":
        return `Ketua RT ${user?.rt_number || "001"}`;
      default:
        return "Staf Kelurahan";
    }
  };

  const getInitials = (name?: string) => {
    if (!name) return "ST";
    const parts = name.trim().split(" ");
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  return (
    <>
      {/* Backdrop overlay for mobile/tablet when drawer is open */}
      <div
        data-testid="sidebar-backdrop"
        onClick={onClose}
        className={`lg:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity duration-300 ${
          isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
      />

      {/* Unified Responsive Sidebar / Drawer */}
      <aside
        data-testid="main-sidebar"
        className={`fixed top-0 left-0 h-screen w-72 lg:w-64 z-50 lg:z-30 bg-primary border-r border-[#0f4c3a] flex flex-col justify-between p-4 text-white select-none transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="flex flex-col gap-4">
          {/* Brand Authority Header */}
          <div className="flex items-center justify-between pb-3 border-b border-[#0f4c3a]">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center p-1.5 border border-white/20 shrink-0">
                <span className="font-bold text-primary-fixed text-base font-mono">JB</span>
              </div>
              <div className="overflow-hidden">
                <h1 className="text-base font-bold text-white tracking-tight leading-tight truncate">
                  EDSS Bansos JUBAR
                </h1>
                <p className="text-[11px] font-mono text-primary-fixed/80 truncate">
                  Kel. Jurangmangu Barat v2.4
                </p>
              </div>
            </div>
            {/* Mobile close button */}
            <button
              type="button"
              aria-label="Tutup menu navigasi"
              onClick={onClose}
              className="lg:hidden p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Quick Batch SAW Button: SUPER_ADMIN ONLY */}
          {userRole === "SUPER_ADMIN" && (
            <button
              type="button"
              onClick={onExecuteSaw}
              className="w-full bg-primary-container hover:bg-[#135d47] text-white text-xs font-semibold py-2.5 px-3 rounded-lg border border-primary-fixed/30 flex items-center justify-center gap-2 transition-all active:scale-95 shadow-sm"
            >
              <Zap className="w-4 h-4 text-emerald-300" />
              <span>Eksekusi Batch SAW</span>
            </button>
          )}

          {/* Navigation Menu */}
          <nav
            aria-label="Menu Utama"
            data-drawer-open={isOpen ? "true" : "false"}
            className="flex flex-col gap-1 overflow-y-auto max-h-[calc(100vh-280px)] custom-scroll pr-1"
          >
            <div className="text-[10px] font-mono tracking-wider uppercase px-3 py-1 text-primary-fixed-dim/70">
              Menu Keputusan
            </div>
            {filteredNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => {
                    if (isOpen) onClose();
                  }}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-primary-container text-white font-semibold shadow-sm border border-emerald-500/20"
                      : "text-white/80 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-emerald-300" : "text-white/70"}`} />
                  <span className="truncate">{item.name}</span>
                  {item.badge && (
                    <span className="ml-auto text-[9px] bg-amber-400/20 text-amber-300 px-1.5 py-0.5 rounded border border-amber-400/30 font-mono">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Footer Profile & Utilities */}
        <div className="flex flex-col gap-3 pt-3 border-t border-[#0f4c3a]">
          <div className="flex items-center justify-between px-2 text-[11px] text-white/60">
            <Link
              to="/docs/api"
              className="flex items-center gap-1.5 hover:text-white transition-colors"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Dokumentasi API</span>
            </Link>
            <Link
              to="/docs/operator"
              className="flex items-center gap-1.5 hover:text-white transition-colors"
            >
              <HelpCircle className="w-3.5 h-3.5" />
              <span>Panduan</span>
            </Link>
          </div>

          {/* Staff Identity Card */}
          <div className="p-2.5 bg-black/25 rounded-lg border border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-lg bg-primary-fixed text-[#002117] font-mono font-bold text-xs flex items-center justify-center shrink-0 border border-primary-fixed-dim">
                {getInitials(user?.name)}
              </div>
              <div className="truncate">
                <p className="text-xs font-semibold text-white truncate leading-tight">
                  {user?.name || "Staf Operator"}
                </p>
                <p className="text-[10px] font-mono text-primary-fixed/80 truncate">
                  {getRoleTitle(userRole)}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={logout}
              title="Keluar Akun"
              aria-label="Keluar Akun"
              className="text-white/60 hover:text-white p-1 rounded hover:bg-white/10 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
