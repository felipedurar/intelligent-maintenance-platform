export type MachineType = 'L' | 'M' | 'H';

export interface Machine {
  id: string;
  name: string;
  type: MachineType;
  status: 'normal' | 'warning' | 'critical';
  lastMaintenance: string;
  telemetry: {
    airTemperature: number;
    processTemperature: number;
    rotationalSpeed: number;
    torque: number;
    toolWear: number;
  };
}

export interface TelemetryPoint {
  timestamp: string;
  airTemperature: number;
  processTemperature: number;
  rotationalSpeed: number;
  torque: number;
}
