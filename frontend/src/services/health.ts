import api from './api';

export interface HealthStatus {
  status: string;
  app: string;
  version: string;
  environment: string;
}

export const healthService = {
  async getHealth(): Promise<HealthStatus> {
    const response = await api.get<HealthStatus>('/health');
    return response.data;
  }
};
