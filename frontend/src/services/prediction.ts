import api from '../services/api';
import type { PredictionRequest, PredictionResponse } from '../types/api';

export const predictionService = {
  async predictFailure(request: PredictionRequest): Promise<PredictionResponse> {
    const response = await api.post<PredictionResponse>('/predictions', request);
    return response.data;
  }
};
