import api from '../../services/api';
import type { ChatRequest, ChatResponse } from './types';

export const chatService = {
  async sendMessage(message: string, sessionId?: string): Promise<ChatResponse> {
    const request: ChatRequest = { message, session_id: sessionId };
    const response = await api.post<ChatResponse>('/chat', request);
    return response.data;
  }
};
