export interface DriftInfo {
  generated_at?: string;
  max_feature_psi?: number;
  drifted_features: string[];
  warning_features: string[];
}

export interface MonitoringStatus {
  status: string;
  metrics: string[];
  message: string;
  latest_report?: string;
  drift: DriftInfo;
}
