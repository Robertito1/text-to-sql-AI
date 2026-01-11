import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('API Module', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe('askQuestion', () => {
    it('should send question to API', async () => {
      const mockResponse = {
        success: true,
        summary: 'Found 100 customers',
        sql: 'SELECT COUNT(*) FROM customers',
        data: [{ count: 100 }],
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const { askQuestion } = await import('../api');
      const result = await askQuestion('How many customers?');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/ask'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
      );
      expect(result.success).toBe(true);
      expect(result.summary).toBe('Found 100 customers');
    });

    it('should include history in request', async () => {
      const mockResponse = { success: true, summary: 'Result' };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const { askQuestion } = await import('../api');
      const history = [
        { role: 'user' as const, content: 'Previous question' },
        { role: 'assistant' as const, content: 'Previous answer' },
      ];

      await askQuestion('Follow up', history);

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('history'),
        })
      );
    });

    it('should throw error on API failure', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      });

      const { askQuestion } = await import('../api');

      await expect(askQuestion('Test')).rejects.toThrow('API error: 500');
    });
  });

  describe('healthCheck', () => {
    it('should return true when API is healthy', async () => {
      global.fetch = vi.fn().mockResolvedValue({ ok: true });

      const { healthCheck } = await import('../api');
      const result = await healthCheck();

      expect(result).toBe(true);
    });

    it('should return false when API is down', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      const { healthCheck } = await import('../api');
      const result = await healthCheck();

      expect(result).toBe(false);
    });
  });
});
