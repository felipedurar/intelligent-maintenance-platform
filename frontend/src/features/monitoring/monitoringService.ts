import api from '../../services/api';
import type { MonitoringStatus } from './types';

export const monitoringService = {
  async getStatus(): Promise<MonitoringStatus> {
    const response = await api.get<MonitoringStatus>('/monitoring/status');
    return response.data;
  }
};
