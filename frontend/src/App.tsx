import React, { useState } from 'react';
import { startRegistration, startAuthentication } from '@simplewebauthn/browser';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

function App() {
  const [registerEmail, setRegisterEmail] = useState('');
  const [loginEmail, setLoginEmail] = useState('');
  const [username, setUsername] = useState('');
  const [message, setMessage] = useState('');
  const [token, setToken] = useState('');

  const handleRegister = async () => {
    try {
      if (!registerEmail || !username) {
        setMessage('Please enter email and username');
        return;
      }

      const optionsRes = await axios.post(`${API_URL}/auth/register/options`, {
        email: registerEmail,
        username
      });

      const credential = await startRegistration(optionsRes.data);

      const verifyRes = await axios.post(`${API_URL}/auth/register/verify`, {
        email: registerEmail,
        credential
      });

      setToken(verifyRes.data.access_token);
      setMessage('Registration successful! You can now use biometric login.');
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || JSON.stringify(error);
      setMessage(`Registration failed: ${errorMsg}`);
    }
  };

  const handleLogin = async () => {
    try {
      if (!loginEmail) {
        setMessage('Please enter your email');
        return;
      }

      const optionsRes = await axios.post(`${API_URL}/auth/login/options`, {
        email: loginEmail
      });

      const credential = await startAuthentication(optionsRes.data);

      const verifyRes = await axios.post(`${API_URL}/auth/login/verify`, {
        email: loginEmail,
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
          type="email"
          placeholder="Email"
          value={loginEmail}
          onChange={(e) => setLoginEmail(e.target.value)}
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
