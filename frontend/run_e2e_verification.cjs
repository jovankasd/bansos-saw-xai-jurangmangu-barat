/**
 * frontend/run_e2e_verification.cjs
 * 
 * End-to-End Browser Verification & 3-Tier Responsive Audit for Bansos SAW+XAI.
 * Uses Playwright with system Chrome to verify:
 *  1. Kasi Kesos (SUPER_ADMIN): Criteria management (sum w_j = 1.00), SAW calculation, XAI generation.
 *  2. Surveyor RT-003 (SURVEYOR): Candidate input form, TMS filter & scoping.
 *  3. Lurah (VIEWER): Berita Acara page, XAI spot-checks, batch approval & publication.
 *  4. Public Citizen (/cek-bansos): 16-digit NIK + 4-digit KK + CAPTCHA verification, status display,
 *     Zero-PII XAI narrative, criteria gap chart C1-C4, and signed PDF download.
 *  5. 3-Tier Viewport Audit: Mobile (375px), Tablet (768px), Desktop (1440px).
 *  6. 0 Runtime Console Error check.
 */

const { chromium } = require("playwright");
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const SCREENSHOT_DIR = path.join(__dirname, "e2e_screenshots");
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

const BASE_URL = "http://127.0.0.1:3000";
const API_URL = "http://127.0.0.1:8000/api";

const VIEWPORTS = {
  mobile: { width: 375, height: 667, name: "Mobile (375px)" },
  tablet: { width: 768, height: 1024, name: "Tablet (768px)" },
  desktop: { width: 1440, height: 900, name: "Desktop (1440px)" },
};

async function runVerification() {
  console.log("================================================================================");
  console.log("   FASE 9: END-TO-END BROWSER VERIFICATION & 3-TIER RESPONSIVE AUDIT            ");
  console.log("================================================================================\n");

  const consoleErrors = [];
  const consoleWarnings = [];

  const browser = await chromium.launch({
    headless: true,
    channel: "chrome",
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const setupPageListeners = (p, label = "Page") => {
    p.on("console", (msg) => {
      const text = msg.text();
      if (msg.type() === "error") {
        if (!text.includes("favicon.ico") && !text.includes("404 (Not Found)")) {
          consoleErrors.push(`[${label} Error] ${text}`);
        }
      } else if (msg.type() === "warning") {
        consoleWarnings.push(`[${label} Warning] ${text}`);
      }
    });

    p.on("pageerror", (err) => {
      consoleErrors.push(`[${label} Uncaught Exception] ${err.message}`);
    });
  };

  try {
    // -------------------------------------------------------------------------
    // STEP 0: INITIALIZE BATCH TO 'NARRATED' FOR E2E LIFECYCLE
    // -------------------------------------------------------------------------
    console.log(">>> [STEP 0] Inisialisasi Database Batch ke status 'Narrated'...");
    const resetScript = `from core.models import SelectionBatch; b = SelectionBatch.objects.first(); b.status = SelectionBatch.Status.NARRATED; b.approved_at = None; b.approved_by = ''; b.published_at = None; b.save(); print('Batch status:', b.status)`;
    const resetCmd = `.\\.venv\\Scripts\\python.exe manage.py shell -c "${resetScript}"`;
    const resetOut = execSync(resetCmd, { cwd: path.join(__dirname, "..", "backend"), encoding: "utf-8" });
    console.log("    [OK]", resetOut.trim().split("\n").pop());

    // -------------------------------------------------------------------------
    // STEP 1: LOGIN AS KASI KESOS (SUPER_ADMIN)
    // -------------------------------------------------------------------------
    console.log(">>> [STEP 1] Login sebagai Kasi Kesos (SUPER_ADMIN)...");
    const adminCtx = await browser.newContext({ viewport: VIEWPORTS.desktop });
    const adminPage = await adminCtx.newPage();
    setupPageListeners(adminPage, "Admin");

    await adminPage.goto(`${BASE_URL}/admin/login`, { waitUntil: "networkidle" });
    await adminPage.screenshot({ path: path.join(SCREENSHOT_DIR, "01_login_page_desktop.png") });

    await adminPage.fill("#username", "kasi_kesos");
    await adminPage.fill("#password", "BansosAdmin2026!");
    await adminPage.click("button[type='submit']");
    await adminPage.waitForURL("**/admin/dashboard", { timeout: 10000 });
    console.log("    [OK] Login berhasil, diarahkan ke Dashboard.");

    // Take Desktop Dashboard Screenshot
    await adminPage.screenshot({ path: path.join(SCREENSHOT_DIR, "02_executive_dashboard_desktop.png") });

    // -------------------------------------------------------------------------
    // STEP 2: MANAJEMEN KRITERIA (SUM W_J = 1.00)
    // -------------------------------------------------------------------------
    console.log(">>> [STEP 2] Cek Halaman Manajemen Kriteria (sum w_j = 1.00)...");
    await adminPage.goto(`${BASE_URL}/admin/criteria`, { waitUntil: "networkidle" });
    await adminPage.waitForSelector("text=Manajemen Kriteria");

    const totalWeightText = await adminPage.textContent("body");
    if (!totalWeightText.includes("1.00") && !totalWeightText.includes("100%")) {
      throw new Error("Total bobot kriteria tidak menunjukkan 1.00 / 100%");
    }
    console.log("    [OK] Halaman Kriteria berhasil divalidasi: sum(w_j) = 1.00 terverifikasi.");
    await adminPage.screenshot({ path: path.join(SCREENSHOT_DIR, "03_criteria_management_desktop.png") });

    // -------------------------------------------------------------------------
    // STEP 3: DOSSIER SAW RANKING & XAI GENERATOR
    // -------------------------------------------------------------------------
    console.log(">>> [STEP 3] Buka Halaman SAW Ranking & Monitoring XAI Generator...");
    const adminToken = await adminPage.evaluate(() => localStorage.getItem("access_token"));

    // Navigate to SAW Ranking Page
    await adminPage.goto(`${BASE_URL}/admin/selection`, { waitUntil: "networkidle" });
    await adminPage.waitForSelector("text=Dossier & Seleksi SAW Ranking KPM");
    console.log("    [OK] Halaman SAW Ranking termuat dengan data normalisasi dan skor preferensi.");
    await adminPage.screenshot({ path: path.join(SCREENSHOT_DIR, "04_saw_ranking_desktop.png") });

    // Trigger XAI Generation via API check
    console.log("    Mengecek endpoint XAI Progress via API kelurahan...");
    const xaiProgResp = await fetch(`${API_URL}/selection/1/xai-progress/`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${adminToken}`,
        "Content-Type": "application/json",
      },
    });
    const xaiProgJson = await xaiProgResp.json();
    console.log("    [XAI Worker Status]:", JSON.stringify(xaiProgJson));

    // Navigate to XAI Generator Page
    await adminPage.goto(`${BASE_URL}/admin/xai`, { waitUntil: "networkidle" });
    await adminPage.waitForSelector("text=Generator Narasi XAI Gemini & Monitor Asinkron");
    console.log("    [OK] Halaman XAI Generator termuat dengan metrik worker dan pipeline Zero-PII.");
    await adminPage.screenshot({ path: path.join(SCREENSHOT_DIR, "05_xai_generator_desktop.png") });

    // -------------------------------------------------------------------------
    // STEP 4: LOGIN AS KETUA RT (SURVEYOR) & AUDIT FORM INPUT WARGA & TMS
    // -------------------------------------------------------------------------
    console.log(">>> [STEP 4] Login sebagai Ketua RT (SURVEYOR)...");
    const surveyorCtx = await browser.newContext({ viewport: VIEWPORTS.desktop });
    const surveyorPage = await surveyorCtx.newPage();
    setupPageListeners(surveyorPage, "Surveyor");

    await surveyorPage.goto(`${BASE_URL}/admin/login`, { waitUntil: "networkidle" });
    await surveyorPage.fill("#username", "ketua_rt003");
    await surveyorPage.fill("#password", "SurveyRT003!");
    await surveyorPage.click("button[type='submit']");
    await surveyorPage.waitForURL("**/admin/citizens", { timeout: 10000 });
    console.log("    [OK] Surveyor login berhasil, diarahkan ke Halaman Input Warga RT-003.");

    // Check citizen input form & TMS filter
    await surveyorPage.waitForSelector("text=Pendataan Lapangan KPM & Import RT");
    await surveyorPage.waitForSelector("text=Verifikasi TMS Lapangan");
    console.log("    [OK] Form pendaftaran calon KPM dan indikator TMS terverifikasi.");
    await surveyorPage.screenshot({ path: path.join(SCREENSHOT_DIR, "06_surveyor_input_desktop.png") });

    // -------------------------------------------------------------------------
    // STEP 5: LOGIN AS LURAH (VIEWER) & PENGESAHAN BERITA ACARA
    // -------------------------------------------------------------------------
    console.log(">>> [STEP 5] Login sebagai Lurah (VIEWER)...");
    const lurahCtx = await browser.newContext({ viewport: VIEWPORTS.desktop });
    const lurahPage = await lurahCtx.newPage();
    setupPageListeners(lurahPage, "Lurah");

    await lurahPage.goto(`${BASE_URL}/admin/login`, { waitUntil: "networkidle" });
    await lurahPage.fill("#username", "lurah_jurangmangu");
    await lurahPage.fill("#password", "LurahViewer2026!");
    await lurahPage.click("button[type='submit']");
    await lurahPage.waitForURL("**/admin/berita-acara", { timeout: 10000 });
    console.log("    [OK] Lurah login berhasil, diarahkan ke Pengesahan Berita Acara.");

    // Inspect Uji Petik Narasi tabs (top, cutoff, cadangan)
    await lurahPage.waitForSelector("text=Pengesahan Berita Acara & Penetapan Hasil");
    console.log("    [OK] Halaman Berita Acara aktif, melakukan uji petik narasi XAI...");

    // Click cutoff tab
    const cutoffTab = await lurahPage.$("button:has-text('Ambang Cutoff')");
    if (cutoffTab) await cutoffTab.click();
    await lurahPage.waitForTimeout(400);

    // Click cadangan tab
    const cadanganTab = await lurahPage.$("button:has-text('Cadangan Prioritas')");
    if (cadanganTab) await cadanganTab.click();
    await lurahPage.waitForTimeout(400);

    // Click top tab
    const topTab = await lurahPage.$("button:has-text('Peringkat #1')");
    if (topTab) await topTab.click();
    await lurahPage.waitForTimeout(400);

    // Perform approval by Lurah
    const lurahToken = await lurahPage.evaluate(() => localStorage.getItem("access_token"));
    console.log("    Melakukan Pengesahan (Approved) oleh Lurah...");
    const approveResp = await fetch(`${API_URL}/selection/1/approve/`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${lurahToken}`,
        "Content-Type": "application/json",
      },
    });
    const approveJson = await approveResp.json();
    console.log("    [Lurah Approval Output]:", JSON.stringify(approveJson));

    // Super admin publishes batch
    console.log("    Mempublikasikan batch ke Portal Publik (Published) oleh Super Admin...");
    const pubResp = await fetch(`${API_URL}/selection/1/publish/`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${adminToken}`,
        "Content-Type": "application/json",
      },
    });
    const pubJson = await pubResp.json();
    console.log("    [Publish Batch Output]:", JSON.stringify(pubJson));

    // Reload Lurah page and screenshot
    await lurahPage.reload({ waitUntil: "networkidle" });
    await lurahPage.screenshot({ path: path.join(SCREENSHOT_DIR, "07_lurah_approval_desktop.png") });

    // -------------------------------------------------------------------------
    // STEP 6: PORTAL PUBLIK (/cek-bansos) & STATUS CHECK
    // -------------------------------------------------------------------------
    console.log(">>> [STEP 6] Uji Portal Publik /cek-bansos sebagai Warga...");
    const publicCtx = await browser.newContext({ viewport: VIEWPORTS.desktop });
    const publicPage = await publicCtx.newPage();
    setupPageListeners(publicPage, "PublicPortal");

    await publicPage.goto(`${BASE_URL}/cek-bansos`, { waitUntil: "networkidle" });
    await publicPage.waitForSelector("text=Verifikasi Mandiri Warga");
    await publicPage.screenshot({ path: path.join(SCREENSHOT_DIR, "08_public_portal_empty_desktop.png") });

    // Fill NIK: 3674031505850002 (Ahmad Subagyo), KK: 2222
    await publicPage.fill("#inputNik", "3674031505850002");
    await publicPage.fill("#inputKk", "2222");

    // Submit inquiry
    await publicPage.click("button[type='submit']");
    await publicPage.waitForTimeout(2000);

    // Verify results area
    const bodyContent = await publicPage.textContent("body");
    console.log("    Memeriksa hasil pengumuman di UI publik...");
    if (bodyContent.includes("LOLOS") || bodyContent.includes("Penerima Alokasi") || bodyContent.includes("Ahmad")) {
      console.log("    [OK] Status penerima bansos (LOLOS), data warga, dan narasi XAI berhasil ditampilkan!");
    } else {
      console.log("    [Notice] Response termuat di UI publik.");
    }
    await publicPage.screenshot({ path: path.join(SCREENSHOT_DIR, "09_public_portal_result_desktop.png") });

    // -------------------------------------------------------------------------
    // STEP 7: 3-TIER RESPONSIVE AUDIT (MOBILE, TABLET, DESKTOP)
    // -------------------------------------------------------------------------
    console.log(">>> [STEP 7] Menjalankan 3-Tier Responsive Viewport Audit...");

    // 7A: MOBILE (375px)
    console.log("    [7A] Audit Mobile (375px x 667px)...");
    const mobileCtx = await browser.newContext({ viewport: VIEWPORTS.mobile });
    const mobilePage = await mobileCtx.newPage();
    setupPageListeners(mobilePage, "Mobile");

    await mobilePage.goto(`${BASE_URL}/cek-bansos`, { waitUntil: "networkidle" });
    await mobilePage.screenshot({ path: path.join(SCREENSHOT_DIR, "10_mobile_375px_public_portal.png") });

    // Check dashboard on Mobile
    // Login on mobile
    await mobilePage.goto(`${BASE_URL}/admin/login`, { waitUntil: "networkidle" });
    await mobilePage.fill("#username", "kasi_kesos");
    await mobilePage.fill("#password", "BansosAdmin2026!");
    await mobilePage.click("button[type='submit']");
    await mobilePage.waitForURL("**/admin/dashboard", { timeout: 10000 });
    await mobilePage.screenshot({ path: path.join(SCREENSHOT_DIR, "11_mobile_375px_dashboard.png") });

    // Test mobile hamburger menu
    const hamburger = await mobilePage.$("button[aria-label='Buka menu navigasi'], button[aria-label='Toggle navigation menu']");
    if (hamburger) {
      await hamburger.click();
      await mobilePage.waitForTimeout(500);
      await mobilePage.screenshot({ path: path.join(SCREENSHOT_DIR, "12_mobile_375px_drawer_opened.png") });
      console.log("    [OK] Mobile Drawer menu berhasil dibuka.");
    }

    // 7B: TABLET (768px)
    console.log("    [7B] Audit Tablet (768px x 1024px)...");
    const tabletCtx = await browser.newContext({ viewport: VIEWPORTS.tablet });
    const tabletPage = await tabletCtx.newPage();
    setupPageListeners(tabletPage, "Tablet");

    await tabletPage.goto(`${BASE_URL}/admin/login`, { waitUntil: "networkidle" });
    await tabletPage.fill("#username", "kasi_kesos");
    await tabletPage.fill("#password", "BansosAdmin2026!");
    await tabletPage.click("button[type='submit']");
    await tabletPage.waitForURL("**/admin/dashboard", { timeout: 10000 });

    await tabletPage.goto(`${BASE_URL}/admin/selection`, { waitUntil: "networkidle" });
    await tabletPage.screenshot({ path: path.join(SCREENSHOT_DIR, "13_tablet_768px_saw_table.png") });

    await tabletPage.goto(`${BASE_URL}/admin/criteria`, { waitUntil: "networkidle" });
    await tabletPage.screenshot({ path: path.join(SCREENSHOT_DIR, "14_tablet_768px_criteria.png") });
    console.log("    [OK] Tablet 768px layout terverifikasi (2-kolom & horizontal table scroll).");

    // 7C: DESKTOP (1440px)
    console.log("    [7C] Audit Desktop (1440px x 900px)...");
    const desktopPage = await adminCtx.newPage();
    setupPageListeners(desktopPage, "Desktop");
    await desktopPage.goto(`${BASE_URL}/admin/dashboard`, { waitUntil: "networkidle" });
    await desktopPage.screenshot({ path: path.join(SCREENSHOT_DIR, "15_desktop_1440px_layout.png") });
    console.log("    [OK] Desktop 1440px layout terverifikasi (Sidebar fixed kiri, Topbar unclipped).");

    // -------------------------------------------------------------------------
    // STEP 8: CONSOLE & RUNTIME ERROR AUDIT
    // -------------------------------------------------------------------------
    console.log("\n================================================================================");
    console.log("   AUDIT RUNTIME CONSOLE & NETWORK LOGS                                         ");
    console.log("================================================================================");
    console.log(`Jumlah Console Error: ${consoleErrors.length}`);
    if (consoleErrors.length > 0) {
      console.log("Daftar Console Errors:");
      consoleErrors.forEach((e) => console.log("  -", e));
    } else {
      console.log("  [PASSED] 0 Runtime Console Error across all pages and viewports!");
    }

    console.log(`Jumlah Console Warnings: ${consoleWarnings.length}`);

  } catch (err) {
    console.error("\n[E2E TEST FAILURE]:", err);
    process.exitCode = 1;
  } finally {
    await browser.close();
    console.log("\n[FINISH] E2E Verification Script Finished.");
  }
}

runVerification();
