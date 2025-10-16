import React, { useState } from 'react';
import { startRegistration, startAuthentication } from '@simplewebauthn/browser';
import axios from 'axios';
import { API_URL } from './config';

function App() {
  const [registerEmail, setRegisterEmail] = useState('');
  const [loginIdentifier, setLoginIdentifier] = useState('');
  const [username, setUsername] = useState('');
  const [message, setMessage] = useState('');
  const [token, setToken] = useState('');

  const handleRegister = async () => {
    try {
      if (!registerEmail || !username) {
        setMessage('Please enter email and username');
        return;
      }

      // Ensure API_URL uses HTTPS
      if (!API_URL.startsWith('https://')) {
        setMessage('Insecure connection detected. Please use HTTPS for all API requests.');
        return;
      }

      let optionsRes;
      try {
        optionsRes = await axios.post(`${API_URL}/auth/register/options`, {
          email: registerEmail,
          username
        });
      } catch (error: any) {
        setMessage(`Failed to get registration options: ${error.response?.data?.detail || error.message}`);
        return;
      }

      let credential;
      try {
        credential = await startRegistration(optionsRes.data);
      } catch (error: any) {
        setMessage(`Biometric registration failed: ${error.message || JSON.stringify(error)}`);
        return;
      }

      let verifyRes;
      try {
        verifyRes = await axios.post(`${API_URL}/auth/register/verify`, {
          email: registerEmail,
          username,
          credential
        });
      } catch (error: any) {
        setMessage(`Failed to verify registration: ${error.response?.data?.detail || error.message}`);
        return;
      }

      setMessage('Registration successful! You can now log in.');
    } catch (error: any) {
      setMessage(`Registration failed: ${error.message || JSON.stringify(error)}`);
    }
  };

  const handleLogin = async () => {
    try {
      if (!loginIdentifier) {
        setMessage('Please enter your email or username');
        return;
      }

      // Ensure API_URL uses HTTPS
      if (!API_URL.startsWith('https://')) {
        setMessage('Insecure connection detected. Please use HTTPS for all API requests.');
        return;
      }
      const optionsRes = await axios.post(`${API_URL}/auth/login/options`, {
        identifier: loginIdentifier
      });

      const credential = await startAuthentication(optionsRes.data);

      // Ensure API_URL uses HTTPS before sending sensitive information
      if (!API_URL.startsWith('https://')) {
        setMessage('Insecure connection detected. Please use HTTPS for all API requests.');
        return;
      }
      const verifyRes = await axios.post(`${API_URL}/auth/login/verify`, {
        identifier: loginIdentifier,
        credential
      });

      setToken(verifyRes.data.access_token);
      setMessage('Login successful!');
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || JSON.stringify(error);
      setMessage(`Login failed: ${errorMsg}`);
    }
  };

  const getUserInfo = async () => {
    try {
      if (!API_URL.startsWith('https://')) {
        setMessage('Insecure connection detected. Please use HTTPS for all API requests.');
        return;
      }
      const res = await axios.get(`${API_URL}/userinfo`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMessage(`User info: ${JSON.stringify(res.data, null, 2)}`);
    } catch (error: any) {
      setMessage(`Failed to get user info: ${error.response?.data?.detail || error.message}`);
    }
  };

  return (
      <div style={{ padding: '40px', maxWidth: '600px', margin: '0 auto' }}>
        <h1>🔐 Hybrid Auth System</h1>
        <p>Passwordless authentication using biometrics (fingerprint, Face ID)</p>

        <div style={{ marginBottom: '20px' }}>
          <h2>Register</h2>
          <input
            type="email"
            placeholder="Email"
            value={registerEmail}
            onChange={(e) => setRegisterEmail(e.target.value)}
            style={{ width: '100%', padding: '10px', marginBottom: '10px' }}
          />
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{ width: '100%', padding: '10px', marginBottom: '10px' }}
          />
          <button onClick={handleRegister} style={{ padding: '10px 20px' }}>
            Register with Biometric
          </button>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <h2>Login</h2>
          <input
            type="text"
            placeholder="Email or Username"
            value={loginIdentifier}
            onChange={(e) => setLoginIdentifier(e.target.value)}
            style={{ width: '100%', padding: '10px', marginBottom: '10px' }}
          />
          <button onClick={handleLogin} style={{ padding: '10px 20px' }}>
            Login with Biometric
          </button>
        </div>

        {token && (
          <div style={{ marginBottom: '20px' }}>
            <button onClick={getUserInfo} style={{ padding: '10px 20px' }}>
              Get User Info
            </button>
          </div>
        )}

        {message && (
          <div style={{
            padding: '15px',
            backgroundColor: '#f0f0f0',
            borderRadius: '5px',
            whiteSpace: 'pre-wrap'
          }}>
            {message}
          </div>
        )}
      </div>
    );
}

export default App;
