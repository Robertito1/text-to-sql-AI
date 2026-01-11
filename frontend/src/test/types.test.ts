import { describe, it, expect } from 'vitest';
import type { QueryResponse, ChartConfig, Message, ConversationMessage } from '../types';

describe('Types', () => {
  describe('QueryResponse', () => {
    it('should have correct structure for success response', () => {
      const response: QueryResponse = {
        success: true,
        summary: 'Found 100 results',
        sql: 'SELECT * FROM users',
        data: [{ id: 1, name: 'Test' }],
        chart: {
          type: 'bar',
          x_key: 'name',
          y_key: 'count',
          title: 'Test Chart',
        },
      };

      expect(response.success).toBe(true);
      expect(response.summary).toBeDefined();
      expect(response.sql).toBeDefined();
      expect(response.data).toHaveLength(1);
      expect(response.chart?.type).toBe('bar');
    });

    it('should have correct structure for error response', () => {
      const response: QueryResponse = {
        success: false,
        summary: 'An error occurred',
        error: 'Database connection failed',
      };

      expect(response.success).toBe(false);
      expect(response.error).toBeDefined();
    });
  });

  describe('ChartConfig', () => {
    it('should support all chart types', () => {
      const chartTypes: ChartConfig['type'][] = ['bar', 'line', 'pie', 'area'];
      
      chartTypes.forEach((type) => {
        const chart: ChartConfig = {
          type,
          x_key: 'x',
          y_key: 'y',
          title: 'Test',
        };
        expect(chart.type).toBe(type);
      });
    });
  });

  describe('Message', () => {
    it('should have correct structure for user message', () => {
      const message: Message = {
        id: '123',
        type: 'user',
        content: 'Hello',
        timestamp: new Date(),
      };

      expect(message.type).toBe('user');
      expect(message.content).toBe('Hello');
    });

    it('should have correct structure for assistant message with response', () => {
      const message: Message = {
        id: '456',
        type: 'assistant',
        content: 'Here are the results',
        response: {
          success: true,
          summary: 'Here are the results',
          data: [],
        },
        timestamp: new Date(),
      };

      expect(message.type).toBe('assistant');
      expect(message.response?.success).toBe(true);
    });
  });

  describe('ConversationMessage', () => {
    it('should have role and content', () => {
      const userMsg: ConversationMessage = {
        role: 'user',
        content: 'Question',
      };

      const assistantMsg: ConversationMessage = {
        role: 'assistant',
        content: 'Answer',
      };

      expect(userMsg.role).toBe('user');
      expect(assistantMsg.role).toBe('assistant');
    });
  });
});
