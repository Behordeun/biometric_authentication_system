import { API_URL } from './config';

describe('Config', () => {
  test('exports API_URL', () => {
    expect(typeof API_URL).toBe('string');
    expect(API_URL).toBeDefined();
  });
});
