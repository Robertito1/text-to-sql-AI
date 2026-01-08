export interface ChartConfig {
  type: 'bar' | 'line' | 'pie' | 'area';
  x_key: string;
  y_key: string;
  title: string;
  x_label?: string;
  y_label?: string;
}

export interface QueryResponse {
  success: boolean;
  summary: string;
  sql?: string;
  data?: Record<string, any>[];
  chart?: ChartConfig;
  error?: string;
}

export interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  response?: QueryResponse;
  timestamp: Date;
}
