import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import axios from 'axios';
import { startRegistration, startAuthentication } from '@simplewebauthn/browser';
import App from './App';

// Mock dependencies
jest.mock('axios');
jest.mock('@simplewebauthn/browser');
jest.mock('./config', () => ({
  API_URL: 'https://localhost:8000'
}));



const mockedAxios = axios as jest.Mocked<typeof axios>;
const mockedStartRegistration = startRegistration as jest.MockedFunction<typeof startRegistration>;
const mockedStartAuthentication = startAuthentication as jest.MockedFunction<typeof startAuthentication>;

describe('App Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders main heading', () => {
    render(<App />);
    expect(screen.getByText('🔐 Hybrid Auth System')).toBeInTheDocument();
  });

  test('renders registration form', () => {
    render(<App />);
    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Username')).toBeInTheDocument();
    expect(screen.getByText('Register with Biometric')).toBeInTheDocument();
  });

  test('renders login form', () => {
    render(<App />);
    expect(screen.getByPlaceholderText('Email or Username')).toBeInTheDocument();
    expect(screen.getByText('Login with Biometric')).toBeInTheDocument();
  });

  test('shows validation message for empty registration fields', async () => {
    render(<App />);

    fireEvent.click(screen.getByText('Register with Biometric'));

    await waitFor(() => {
      expect(screen.getByText('Please enter first name, last name, username, and email')).toBeInTheDocument();
    });
  });

  test('shows validation message for empty login field', async () => {
    render(<App />);

    fireEvent.click(screen.getByText('Login with Biometric'));

    await waitFor(() => {
      expect(screen.getByText('Please enter your email or username')).toBeInTheDocument();
    });
  });

  test('successful registration flow', async () => {
    const mockOptionsResponse = { data: { challenge: 'test-challenge' } };
    const mockCredential = { id: 'test-credential' };
    const mockVerifyResponse = { data: { success: true } };

    mockedAxios.post
      .mockResolvedValueOnce(mockOptionsResponse)
      .mockResolvedValueOnce(mockVerifyResponse);
    mockedStartRegistration.mockResolvedValue(mockCredential as any);

    render(<App />);

    // Fill registration form
    const firstNameInput = screen.getByPlaceholderText('First Name');
    const lastNameInput = screen.getByPlaceholderText('Last Name');
    const emailInput = screen.getByPlaceholderText('Email');
    const usernameInput = screen.getByPlaceholderText('Username');

    fireEvent.change(firstNameInput, { target: { value: 'Test' } });
    fireEvent.change(lastNameInput, { target: { value: 'User' } });
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });

    // Click register
    fireEvent.click(screen.getByText('Register with Biometric'));

    await waitFor(() => {
      expect(screen.getByText('Registration successful! You can now log in.')).toBeInTheDocument();
    });
  });

  test('successful login flow', async () => {
    const mockOptionsResponse = { data: { challenge: 'test-challenge' } };
    const mockCredential = { id: 'test-credential' };
    const mockVerifyResponse = { data: { access_token: 'test-token' } };

    mockedAxios.post
      .mockResolvedValueOnce(mockOptionsResponse)
      .mockResolvedValueOnce(mockVerifyResponse);
    mockedStartAuthentication.mockResolvedValue(mockCredential as any);

    render(<App />);

    // Fill login form
    const loginInput = screen.getByPlaceholderText('Email or Username');
    fireEvent.change(loginInput, { target: { value: 'test@example.com' } });

    // Click login
    fireEvent.click(screen.getByText('Login with Biometric'));

    await waitFor(() => {
      expect(screen.getByText('Login successful!')).toBeInTheDocument();
      expect(screen.getByText('Get User Info')).toBeInTheDocument();
    });
  });

  test('handles registration API error', async () => {
    mockedAxios.post.mockRejectedValue({
      response: { data: { detail: 'User already exists' } }
    });

    render(<App />);

    const firstNameInput = screen.getByPlaceholderText('First Name');
    const lastNameInput = screen.getByPlaceholderText('Last Name');
    const emailInput = screen.getByPlaceholderText('Email');
    const usernameInput = screen.getByPlaceholderText('Username');

    fireEvent.change(firstNameInput, { target: { value: 'Test' } });
    fireEvent.change(lastNameInput, { target: { value: 'User' } });
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.click(screen.getByText('Register with Biometric'));

    await waitFor(() => {
      expect(screen.getByText(/Failed to get registration options: User already exists/)).toBeInTheDocument();
    });
  });

  test('handles login API error', async () => {
    mockedAxios.post.mockRejectedValue({
      response: { data: { detail: 'User not found' } }
    });

    render(<App />);

    const loginInput = screen.getByPlaceholderText('Email or Username');
    fireEvent.change(loginInput, { target: { value: 'test@example.com' } });
    fireEvent.click(screen.getByText('Login with Biometric'));

    await waitFor(() => {
      expect(screen.getByText(/Login failed: User not found/)).toBeInTheDocument();
    });
  });

  test('handles biometric registration failure', async () => {
    const mockOptionsResponse = { data: { challenge: 'test-challenge' } };
    mockedAxios.post.mockResolvedValue(mockOptionsResponse);
    mockedStartRegistration.mockRejectedValue(new Error('Biometric not supported'));

    render(<App />);

    const firstNameInput = screen.getByPlaceholderText('First Name');
    const lastNameInput = screen.getByPlaceholderText('Last Name');
    const emailInput = screen.getByPlaceholderText('Email');
    const usernameInput = screen.getByPlaceholderText('Username');

    fireEvent.change(firstNameInput, { target: { value: 'Test' } });
    fireEvent.change(lastNameInput, { target: { value: 'User' } });
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.click(screen.getByText('Register with Biometric'));

    await waitFor(() => {
      expect(screen.getByText(/Biometric registration failed: Biometric not supported/)).toBeInTheDocument();
    });
  });

  test('get user info functionality', async () => {
    // First login
    const mockOptionsResponse = { data: { challenge: 'test-challenge' } };
    const mockCredential = { id: 'test-credential' };
    const mockVerifyResponse = { data: { access_token: 'test-token' } };
    const mockUserInfoResponse = { data: { id: '1', email: 'test@example.com' } };

    mockedAxios.post
      .mockResolvedValueOnce(mockOptionsResponse)
      .mockResolvedValueOnce(mockVerifyResponse);
    mockedAxios.get.mockResolvedValue(mockUserInfoResponse);
    mockedStartAuthentication.mockResolvedValue(mockCredential as any);

    render(<App />);

    // Login first
    const loginInput = screen.getByPlaceholderText('Email or Username');
    fireEvent.change(loginInput, { target: { value: 'test@example.com' } });
    fireEvent.click(screen.getByText('Login with Biometric'));

    await waitFor(() => {
      expect(screen.getByText('Get User Info')).toBeInTheDocument();
    });

    // Get user info
    fireEvent.click(screen.getByText('Get User Info'));

    await waitFor(() => {
      expect(screen.getByText(/User info:/)).toBeInTheDocument();
    });
  });

  test('handles user info API error', async () => {
    // First login
    const mockOptionsResponse = { data: { challenge: 'test-challenge' } };
    const mockCredential = { id: 'test-credential' };
    const mockVerifyResponse = { data: { access_token: 'test-token' } };

    mockedAxios.post
      .mockResolvedValueOnce(mockOptionsResponse)
      .mockResolvedValueOnce(mockVerifyResponse);
    mockedAxios.get.mockRejectedValue({
      response: { data: { detail: 'Unauthorized' } }
    });
    mockedStartAuthentication.mockResolvedValue(mockCredential as any);

    render(<App />);

    // Login first
    const loginInput = screen.getByPlaceholderText('Email or Username');
    fireEvent.change(loginInput, { target: { value: 'test@example.com' } });
    fireEvent.click(screen.getByText('Login with Biometric'));

    await waitFor(() => {
      expect(screen.getByText('Get User Info')).toBeInTheDocument();
    });

    // Get user info with error
    fireEvent.click(screen.getByText('Get User Info'));

    await waitFor(() => {
      expect(screen.getByText(/Failed to get user info: Unauthorized/)).toBeInTheDocument();
    });
  });

  test('handles registration verification failure', async () => {
    const mockOptionsResponse = { data: { challenge: 'test-challenge' } };
    const mockCredential = { id: 'test-credential' };

    mockedAxios.post
      .mockResolvedValueOnce(mockOptionsResponse)
      .mockRejectedValueOnce({
        response: { data: { detail: 'Verification failed' } }
      });
    mockedStartRegistration.mockResolvedValue(mockCredential as any);

    render(<App />);

    const firstNameInput = screen.getByPlaceholderText('First Name');
    const lastNameInput = screen.getByPlaceholderText('Last Name');
    const emailInput = screen.getByPlaceholderText('Email');
    const usernameInput = screen.getByPlaceholderText('Username');

    fireEvent.change(firstNameInput, { target: { value: 'Test' } });
    fireEvent.change(lastNameInput, { target: { value: 'User' } });
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.click(screen.getByText('Register with Biometric'));

    await waitFor(() => {
      expect(screen.getByText(/Failed to verify registration: Verification failed/)).toBeInTheDocument();
    });
  });

  test('handles authentication biometric failure', async () => {
    const mockOptionsResponse = { data: { challenge: 'test-challenge' } };
    mockedAxios.post.mockResolvedValue(mockOptionsResponse);
    mockedStartAuthentication.mockRejectedValue(new Error('Biometric failed'));

    render(<App />);

    const loginInput = screen.getByPlaceholderText('Email or Username');
    fireEvent.change(loginInput, { target: { value: 'test@example.com' } });
    fireEvent.click(screen.getByText('Login with Biometric'));

    await waitFor(() => {
      expect(screen.getByText(/Login failed: Biometric failed/)).toBeInTheDocument();
    });
  });

  test('handles registration with middle name', async () => {
    const mockOptionsResponse = { data: { challenge: 'test-challenge' } };
    const mockCredential = { id: 'test-credential' };
    const mockVerifyResponse = { data: { success: true } };

    mockedAxios.post
      .mockResolvedValueOnce(mockOptionsResponse)
      .mockResolvedValueOnce(mockVerifyResponse);
    mockedStartRegistration.mockResolvedValue(mockCredential as any);

    render(<App />);

    // Fill registration form with middle name
    const firstNameInput = screen.getByPlaceholderText('First Name');
    const middleNameInput = screen.getByPlaceholderText('Middle Name (Optional)');
    const lastNameInput = screen.getByPlaceholderText('Last Name');
    const emailInput = screen.getByPlaceholderText('Email');
    const usernameInput = screen.getByPlaceholderText('Username');

    fireEvent.change(firstNameInput, { target: { value: 'Test' } });
    fireEvent.change(middleNameInput, { target: { value: 'Middle' } });
    fireEvent.change(lastNameInput, { target: { value: 'User' } });
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });

    // Click register
    fireEvent.click(screen.getByText('Register with Biometric'));

    await waitFor(() => {
      expect(screen.getByText('Registration successful! You can now log in.')).toBeInTheDocument();
    });
  });

  test('handles generic registration error without response data', async () => {
    mockedAxios.post.mockRejectedValue(new Error('Network error'));

    render(<App />);

    const firstNameInput = screen.getByPlaceholderText('First Name');
    const lastNameInput = screen.getByPlaceholderText('Last Name');
    const emailInput = screen.getByPlaceholderText('Email');
    const usernameInput = screen.getByPlaceholderText('Username');

    fireEvent.change(firstNameInput, { target: { value: 'Test' } });
    fireEvent.change(lastNameInput, { target: { value: 'User' } });
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.click(screen.getByText('Register with Biometric'));

    await waitFor(() => {
      expect(screen.getByText(/Failed to get registration options: Network error/)).toBeInTheDocument();
    });
  });

  test('handles array error details in registration verification', async () => {
    const mockOptionsResponse = { data: { challenge: 'test-challenge' } };
    const mockCredential = { id: 'test-credential' };

    mockedAxios.post
      .mockResolvedValueOnce(mockOptionsResponse)
      .mockRejectedValueOnce({
        response: {
          data: {
            detail: [
              { loc: ['field1'], msg: 'Error 1' },
              { loc: ['field2'], msg: 'Error 2' }
            ]
          }
        }
      });
    mockedStartRegistration.mockResolvedValue(mockCredential as any);

    render(<App />);

    const firstNameInput = screen.getByPlaceholderText('First Name');
    const lastNameInput = screen.getByPlaceholderText('Last Name');
    const emailInput = screen.getByPlaceholderText('Email');
    const usernameInput = screen.getByPlaceholderText('Username');

    fireEvent.change(firstNameInput, { target: { value: 'Test' } });
    fireEvent.change(lastNameInput, { target: { value: 'User' } });
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.click(screen.getByText('Register with Biometric'));

    await waitFor(() => {
      expect(screen.getByText(/Failed to verify registration: field1: Error 1, field2: Error 2/)).toBeInTheDocument();
    });
  });
});
