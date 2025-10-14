import { browserSupportsWebAuthn } from '@simplewebauthn/browser';

jest.mock('@simplewebauthn/browser', () => ({
  browserSupportsWebAuthn: jest.fn(),
}));

const mockedBrowserSupportsWebAuthn = browserSupportsWebAuthn as jest.MockedFunction<typeof browserSupportsWebAuthn>;

describe('WebAuthn Utils', () => {
  test('checks browser support', () => {
    mockedBrowserSupportsWebAuthn.mockReturnValue(true);
    expect(browserSupportsWebAuthn()).toBe(true);

    mockedBrowserSupportsWebAuthn.mockReturnValue(false);
    expect(browserSupportsWebAuthn()).toBe(false);
  });
});
