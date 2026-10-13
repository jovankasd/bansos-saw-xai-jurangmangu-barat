export interface CriterionGapItem {
  kriteria: string;
  skor_pemohon: number;
  rata_rata_lolos: number;
}

export interface ExplanationData {
  ringkasan: string;
  faktor_utama: string[];
  narasi_lengkap: string;
  rekomendasi: string;
}

export interface ApplicantMasked {
  nik_masked: string;
  name_masked: string;
  rt: string;
  rw: string;
}

export interface SelectionResultPublic {
  status: "LOLOS" | "TIDAK_LOLOS" | "DISKUALIFIKASI_TMS" | string;
  rank: number;
  quota: number;
  final_score: number;
  cutoff_score: number;
  explanation: ExplanationData;
  chart_data: CriterionGapItem[];
}

export interface PublicCheckStatusResponse {
  found: boolean;
  period_name: string;
  download_token?: string;
  applicant?: ApplicantMasked;
  result?: SelectionResultPublic;
  message?: string;
}
