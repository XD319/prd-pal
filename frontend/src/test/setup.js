import '@testing-library/jest-dom';
import { afterEach, vi } from 'vitest';

const createMatchMediaMock = (matches = false) => (query) => ({
  matches,
  media: query,
  onchange: null,
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  addListener: vi.fn(),
  removeListener: vi.fn(),
  dispatchEvent: vi.fn(),
});

const defaultFetchResponse = {
  ok: true,
  status: 200,
  json: async () => ({}),
  text: async () => '',
};

if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: vi.fn(createMatchMediaMock()),
  });

  Object.defineProperty(window, 'fetch', {
    writable: true,
    configurable: true,
    value: vi.fn(async () => defaultFetchResponse),
  });

  Object.defineProperty(globalThis, 'fetch', {
    writable: true,
    configurable: true,
    value: window.fetch,
  });
}

afterEach(() => {
  window.fetch.mockClear();
  window.matchMedia.mockClear();
});
