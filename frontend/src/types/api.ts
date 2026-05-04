export interface DatasetStatus {
  status: string;
  dataset: string;
  message: string;
  expected_columns: string[];
}

export interface MachineObservation {
  product_type: 'L' | 'M' | 'H';
  air_temperature_k: number;
  process_temperature_k: number;
  rotational_speed_rpm: number;
  torque_nm: number;
  tool_wear_min: number;
}

export interface PredictionRequest {
  observation: MachineObservation;
  request_id?: string;
}

export interface PredictionResponse {
  status: string;
  failure_probability?: number;
  risk_class?: string;
  model_version?: string;
  message: string;
  metadata: Record<string, any>;
}
