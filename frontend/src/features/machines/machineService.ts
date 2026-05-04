import api from '../../services/api';
import type { DatasetStatus } from '../../types/api';

export const machineService = {
  async getDatasetStatus(): Promise<DatasetStatus> {
    const response = await api.get<DatasetStatus>('/machines/dataset/status');
    return response.data;
  }
};
