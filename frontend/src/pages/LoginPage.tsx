import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldCheck, AlertCircle, User, Lock, Eye, EyeOff, LogIn, ArrowLeft } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsLoading(true);

    try {
      const response = await api.post("/auth/login/", {
        username,
        password,
      });

      const { access, refresh, role, name, rt_number } = response.data;
      login(access, refresh, { name, role, rt_number });

      // Role-based navigation to actual registered routes
      if (role === "SUPER_ADMIN") {
        navigate("/admin/dashboard");
      } else if (role === "SURVEYOR") {
        navigate("/admin/citizens");
      } else if (role === "VIEWER") {
        navigate("/admin/berita-acara");
      } else {
        navigate("/admin/dashboard");
      }
    } catch (err: any) {
      if (err.response?.status === 401) {
        setErrorMsg("Username atau kata sandi tidak valid.");
      } else if (err.response?.status === 403) {
        setErrorMsg("Akun staf tidak aktif. Silakan hubungi Administrator.");
      } else if (err.response?.status === 429) {
        setErrorMsg("Terlalu banyak percobaan login. Silakan tunggu 1 menit.");
      } else {
        setErrorMsg(
          err.response?.data?.error || "Gagal masuk ke sistem. Periksa kembali kredensial Anda."
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface font-body-md text-on-surface flex flex-col justify-center py-12 sm:px-6 lg:px-8 antialiased">
      <div className="sm:mx-auto sm:w-full sm:max-w-md px-4">
        {/* Civic Logo & Branding Header */}
        <div className="text-center space-y-2">
          <div className="mx-auto w-14 h-14 rounded-2xl bg-primary text-on-primary flex items-center justify-center shadow-md">
            <ShieldCheck className="w-8 h-8 text-on-primary" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-primary">
            Panel Adjudikasi Bansos
          </h1>
          <p className="text-xs font-mono uppercase text-secondary tracking-wider">
            Pemerintah Kelurahan Jurangmangu Barat
          </p>
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div className="bg-surface-container-lowest py-8 px-6 sm:px-10 shadow-sm border border-border-subtle rounded-2xl space-y-6">
          <div className="border-b border-border-subtle pb-3">
            <h2 className="text-base font-bold text-on-surface">Masuk Akun Staf</h2>
            <p className="text-xs text-secondary mt-0.5">
              Khusus Operator Kasi Kesos, Surveyor RT, dan Pimpinan Kelurahan
            </p>
          </div>

          {errorMsg && (
            <div className="p-3.5 rounded-xl bg-status-rejected-bg border border-red-200 text-status-rejected-fg text-xs sm:text-sm flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-status-rejected-fg" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            {/* Username / NIP */}
            <div className="space-y-1.5">
              <label
                htmlFor="username"
                className="block text-xs font-bold text-on-surface uppercase tracking-wider"
              >
                Nama Pengguna / NIP
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-secondary">
                  <User className="w-4 h-4 text-secondary" />
                </span>
                <input
                  id="username"
                  aria-label="Nama Pengguna / NIP"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Contoh: kasi_kesos"
                  required
                  className="w-full pl-10 pr-4 py-2.5 bg-surface-canvas rounded-xl text-on-surface text-sm border border-border-subtle focus:outline-none focus:ring-2 focus:ring-primary shadow-inner"
                />
              </div>
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label
                htmlFor="password"
                className="block text-xs font-bold text-on-surface uppercase tracking-wider"
              >
                Kata Sandi Akun
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-secondary">
                  <Lock className="w-4 h-4 text-secondary" />
                </span>
                <input
                  id="password"
                  aria-label="Kata Sandi Akun"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full pl-10 pr-10 py-2.5 bg-surface-canvas rounded-xl text-on-surface text-sm border border-border-subtle focus:outline-none focus:ring-2 focus:ring-primary shadow-inner"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-secondary hover:text-primary"
                  tabIndex={-1}
                  aria-label={showPassword ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"}
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full min-h-[44px] py-2.5 px-4 bg-primary text-on-primary rounded-xl text-sm font-semibold hover:bg-primary-container disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 shadow-sm"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-on-primary border-t-transparent rounded-full animate-spin" />
                    <span>Memverifikasi Akses...</span>
                  </>
                ) : (
                  <>
                    <LogIn className="w-4 h-4" />
                    <span>Masuk ke Panel Adjudikasi</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Back to Public Portal */}
          <div className="border-t border-border-subtle pt-4 text-center">
            <Link
              to="/cek-bansos"
              className="inline-flex items-center gap-1.5 text-xs text-primary font-medium hover:underline"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Kembali ke Portal Publik Cek Bansos</span>
            </Link>
          </div>
        </div>

        {/* Security Notice */}
        <p className="mt-4 text-center font-mono text-[11px] text-secondary">
          Sistem Terlindungi Autentikasi Kriptografis JWT &amp; Audit Trail Kelurahan
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
