import React, { useState, useEffect, createContext, useContext } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [notifications, setNotifications] = useState([]);
  const [wsConnection, setWsConnection] = useState(null);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchCurrentUser();
      setupWebSocket();
    }
  }, [token]);

  const setupWebSocket = () => {
    if (user && !wsConnection) {
      const ws = new WebSocket(`${BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://')}/ws/${user.id}`);
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'notification') {
          setNotifications(prev => [data.data, ...prev]);
        }
      };
      
      ws.onopen = () => {
        console.log('WebSocket connected');
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setWsConnection(null);
      };
      
      setWsConnection(ws);
    }
  };

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get(`${API}/users/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching user:', error);
      logout();
    }
  };

  const fetchNotifications = async () => {
    try {
      const response = await axios.get(`${API}/notifications`);
      setNotifications(response.data);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token, user_id, role } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      return { success: true, role };
    } catch (error) {
      console.error('Login error:', error);
      
      // Handle different types of errors
      let errorMessage = 'Login failed';
      
      if (error.response?.data?.detail) {
        // Handle single error message
        if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        } else if (Array.isArray(error.response.data.detail)) {
          // Handle Pydantic validation errors
          errorMessage = error.response.data.detail.map(err => {
            if (typeof err === 'string') return err;
            if (err.msg) return `${err.loc ? err.loc.join('.') + ': ' : ''}${err.msg}`;
            return 'Validation error';
          }).join('; ');
        } else if (typeof error.response.data.detail === 'object') {
          // Handle object errors
          errorMessage = 'Please check your login credentials';
        }
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      return { success: false, error: errorMessage };
    }
  };

  const register = async (userData) => {
    try {
      const response = await axios.post(`${API}/auth/register`, userData);
      const { access_token, user_id, role } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      return { success: true, role };
    } catch (error) {
      console.error('Registration error:', error);
      
      // Handle different types of errors
      let errorMessage = 'Registration failed';
      
      if (error.response?.data?.detail) {
        // Handle single error message
        if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        } else if (Array.isArray(error.response.data.detail)) {
          // Handle Pydantic validation errors
          errorMessage = error.response.data.detail.map(err => {
            if (typeof err === 'string') return err;
            if (err.msg) return `${err.loc ? err.loc.join('.') + ': ' : ''}${err.msg}`;
            return 'Validation error';
          }).join('; ');
        } else if (typeof error.response.data.detail === 'object') {
          // Handle object errors
          errorMessage = JSON.stringify(error.response.data.detail);
        }
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      return { success: false, error: errorMessage };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setNotifications([]);
    if (wsConnection) {
      wsConnection.close();
      setWsConnection(null);
    }
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      login, 
      register, 
      logout, 
      token, 
      notifications, 
      fetchNotifications 
    }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Components
const Header = () => {
  const { user, logout, notifications } = useAuth();
  const [showNotifications, setShowNotifications] = useState(false);

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <header className="bg-gradient-to-r from-blue-600 to-blue-800 text-white p-4 shadow-lg">
      <div className="container mx-auto flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-700 rounded-lg flex items-center justify-center shadow-lg">
              <span className="text-white font-bold text-lg">PMA</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold">Prescription Management App</h1>
              <span className="text-xs text-blue-200">Powered by Innovating Chaos</span>
            </div>
          </div>
          <span className="text-sm bg-blue-500 px-2 py-1 rounded-full">
            Healthcare Innovation • WCAG 2.2 AA
          </span>
        </div>
        
        {user && (
          <div className="flex items-center space-x-4">
            {/* Notifications */}
            <div className="relative">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative p-2 bg-blue-500 rounded-full hover:bg-blue-400 transition-colors"
                aria-label="Notifications"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
                </svg>
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                    {unreadCount}
                  </span>
                )}
              </button>
              
              {showNotifications && (
                <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
                  <div className="p-4 border-b border-gray-200">
                    <h3 className="font-semibold text-gray-800">Notifications</h3>
                  </div>
                  <div className="max-h-64 overflow-y-auto">
                    {notifications.length === 0 ? (
                      <div className="p-4 text-center text-gray-500">
                        No notifications
                      </div>
                    ) : (
                      notifications.slice(0, 5).map((notification) => (
                        <div key={notification.id} className={`p-3 border-b border-gray-100 ${!notification.is_read ? 'bg-blue-50' : ''}`}>
                          <div className="font-medium text-gray-800 text-sm">
                            {notification.title}
                          </div>
                          <div className="text-gray-600 text-xs mt-1">
                            {notification.message}
                          </div>
                          <div className="text-gray-400 text-xs mt-1">
                            {new Date(notification.created_at).toLocaleString()}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
            
            <div className="flex items-center space-x-2">
              <div className="text-right">
                <div className="text-sm font-medium">{user.full_name}</div>
                <div className="text-sm text-blue-200">
                  {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                  {user.nhs_number && (
                    <span className="ml-2">ID: {user.nhs_number}</span>
                  )}
                </div>
              </div>
              <button
                onClick={logout}
                className="bg-red-500 hover:bg-red-600 px-3 py-1 rounded text-sm transition-colors"
                aria-label="Logout"
              >
                Logout
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
};

const LoginForm = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'patient',
    nhs_number: '',
    phone: '',
    address: '',
    date_of_birth: '',
    gp_license_number: '',
    pharmacy_license_number: '',
    ods_code: '',
    gdpr_consent: false
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      let result;
      if (isLogin) {
        result = await login(formData.email, formData.password);
      } else {
        if (!formData.gdpr_consent) {
          setError('GDPR consent is required');
          setLoading(false);
          return;
        }
        
        // Clean up the form data - only send non-empty values
        const cleanFormData = {
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name,
          role: formData.role,
          gdpr_consent: formData.gdpr_consent
        };
        
        // Only include optional fields if they have values
        if (formData.nhs_number && formData.nhs_number.trim()) {
          cleanFormData.nhs_number = formData.nhs_number.trim();
        }
        if (formData.phone && formData.phone.trim()) {
          cleanFormData.phone = formData.phone.trim();
        }
        if (formData.address && formData.address.trim()) {
          cleanFormData.address = formData.address.trim();
        }
        if (formData.date_of_birth && formData.date_of_birth.trim()) {
          cleanFormData.date_of_birth = formData.date_of_birth.trim();
        }
        if (formData.gp_license_number && formData.gp_license_number.trim()) {
          cleanFormData.gp_license_number = formData.gp_license_number.trim();
        }
        if (formData.pharmacy_license_number && formData.pharmacy_license_number.trim()) {
          cleanFormData.pharmacy_license_number = formData.pharmacy_license_number.trim();
        }
        if (formData.ods_code && formData.ods_code.trim()) {
          cleanFormData.ods_code = formData.ods_code.trim();
        }
        
        result = await register(cleanFormData);
      }

      if (!result.success) {
        setError(result.error);
      }
    } catch (err) {
      setError('An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center p-4">
      <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-md border border-blue-200">
        <div className="text-center mb-6">
          <div className="flex justify-center mb-4">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center shadow-xl">
              <span className="text-white font-bold text-2xl">PMA</span>
            </div>
          </div>
          <h2 className="text-3xl font-bold text-gray-800 mb-2">
            {isLogin ? 'Welcome Back' : 'Join PMA'}
          </h2>
          <p className="text-gray-600">
            {isLogin ? 'Sign in to your healthcare account' : 'Create your secure healthcare account'}
          </p>
          <p className="text-sm text-blue-600 mt-2 font-medium">
            Prescription Management App
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Powered by Innovating Chaos
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email Address
            </label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="your.email@example.com"
              aria-describedby="email-help"
            />
            <div id="email-help" className="text-xs text-gray-500 mt-1">
              Use your secure email address
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              required
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="••••••••"
              aria-describedby="password-help"
            />
            <div id="password-help" className="text-xs text-gray-500 mt-1">
              Use a strong password with at least 8 characters
            </div>
          </div>

          {!isLogin && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="John Doe"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Role
                </label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value})}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  aria-describedby="role-help"
                >
                  <option value="patient">Patient</option>
                  <option value="gp">GP (General Practitioner)</option>
                  <option value="pharmacy">Pharmacy</option>
                  <option value="delegate">Delegate/Carer</option>
                </select>
                <div id="role-help" className="text-xs text-gray-500 mt-1">
                  Select your role in the healthcare system
                </div>
              </div>

              {formData.role === 'patient' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Patient ID Number
                  </label>
                  <input
                    type="text"
                    value={formData.nhs_number}
                    onChange={(e) => setFormData({...formData, nhs_number: e.target.value})}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Patient123456"
                    maxLength="10"
                    aria-describedby="patient-help"
                  />
                  <div id="patient-help" className="text-xs text-gray-500 mt-1">
                    Your unique patient identifier (optional)
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Phone Number
                </label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({...formData, phone: e.target.value})}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="+44 7700 900123"
                />
              </div>

              {formData.role === 'gp' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    GP License Number
                  </label>
                  <input
                    type="text"
                    value={formData.gp_license_number}
                    onChange={(e) => setFormData({...formData, gp_license_number: e.target.value})}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="GMC123456"
                    aria-describedby="gp-license-help"
                  />
                  <div id="gp-license-help" className="text-xs text-gray-500 mt-1">
                    Your GMC license number (optional)
                  </div>
                </div>
              )}

              {formData.role === 'pharmacy' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Pharmacy License Number
                  </label>
                  <input
                    type="text"
                    value={formData.pharmacy_license_number}
                    onChange={(e) => setFormData({...formData, pharmacy_license_number: e.target.value})}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="GPhC987654"
                    aria-describedby="pharmacy-license-help"
                  />
                  <div id="pharmacy-license-help" className="text-xs text-gray-500 mt-1">
                    Your GPhC license number (optional)
                  </div>
                </div>
              )}

              <div className="flex items-start space-x-3">
                <input
                  type="checkbox"
                  id="gdpr-consent"
                  checked={formData.gdpr_consent}
                  onChange={(e) => setFormData({...formData, gdpr_consent: e.target.checked})}
                  className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  required
                />
                <label htmlFor="gdpr-consent" className="text-sm text-gray-700">
                  I consent to the processing of my personal data in accordance with GDPR and healthcare data protection standards. 
                  <a href="#" className="text-blue-600 hover:text-blue-800 underline ml-1">
                    Learn more
                  </a>
                </label>
              </div>
            </>
          )}

          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg" role="alert">
              <span className="font-medium">Error:</span>
              <div className="mt-1 text-sm">
                {typeof error === 'string' ? error : JSON.stringify(error)}
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-blue-700 text-white py-3 px-4 rounded-lg hover:from-blue-700 hover:to-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 font-medium"
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing...
              </span>
            ) : (
              isLogin ? 'Sign In Securely' : 'Create Account'
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-blue-600 hover:text-blue-800 font-medium transition-colors"
          >
            {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>

        <div className="mt-6 text-center text-xs text-gray-500">
          <p>🔒 Secured by healthcare-grade encryption</p>
          <p>♿ WCAG 2.2 AA Compliant • GDPR Compliant</p>
          <p className="text-blue-600 font-medium mt-2">
            Prescription Management App (PMA)
          </p>
          <p className="text-blue-600 font-medium">
            Powered by Innovating Chaos
          </p>
        </div>
      </div>
    </div>
  );
};

const PatientDashboard = () => {
  const [prescriptions, setPrescriptions] = useState([]);
  const [showNewPrescription, setShowNewPrescription] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [newPrescription, setNewPrescription] = useState({
    medication_name: '',
    dosage: '',
    quantity: '',
    instructions: '',
    notes: '',
    priority: 'normal',
    prescription_type: 'acute'
  });
  const [loading, setLoading] = useState(false);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [selectedPrescription, setSelectedPrescription] = useState(null);
  const { user } = useAuth();

  useEffect(() => {
    fetchPrescriptions();
  }, []);

  const fetchPrescriptions = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/prescriptions`);
      setPrescriptions(response.data);
    } catch (error) {
      console.error('Error fetching prescriptions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePrescription = async (e) => {
    e.preventDefault();
    setSubmitLoading(true);
    
    try {
      const response = await axios.post(`${API}/prescriptions`, newPrescription);
      
      // Reset form
      setNewPrescription({
        medication_name: '',
        dosage: '',
        quantity: '',
        instructions: '',
        notes: '',
        priority: 'normal',
        prescription_type: 'acute'
      });
      
      // Show success message
      setShowNewPrescription(false);
      setShowSuccess(true);
      
      // Refresh prescriptions
      fetchPrescriptions();
      
      // Hide success message after 5 seconds
      setTimeout(() => {
        setShowSuccess(false);
      }, 5000);
      
    } catch (error) {
      console.error('Error creating prescription:', error);
      
      let errorMessage = 'Error creating prescription. Please try again.';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.status === 403) {
        errorMessage = 'You do not have permission to create prescriptions.';
      } else if (error.response?.status === 401) {
        errorMessage = 'Please log in again to create prescriptions.';
      }
      
      // Show error message in a more user-friendly way
      const errorDiv = document.createElement('div');
      errorDiv.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-4 rounded-lg shadow-lg z-50';
      errorDiv.innerHTML = `
        <div class="flex items-center">
          <svg class="w-6 h-6 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <div>
            <p class="font-medium">Error</p>
            <p class="text-sm opacity-90">${errorMessage}</p>
          </div>
        </div>
      `;
      document.body.appendChild(errorDiv);
      
      // Remove error message after 5 seconds
      setTimeout(() => {
        if (document.body.contains(errorDiv)) {
          document.body.removeChild(errorDiv);
        }
      }, 5000);
      
    } finally {
      setSubmitLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'requested': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'gp_approved': return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'sent_to_pharmacy': return 'bg-purple-100 text-purple-800 border-purple-300';
      case 'dispensed': return 'bg-green-100 text-green-800 border-green-300';
      case 'ready_for_collection': return 'bg-green-100 text-green-800 border-green-300';
      case 'collected': return 'bg-gray-100 text-gray-800 border-gray-300';
      default: return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'requested': return 'Pending GP Approval';
      case 'gp_approved': return 'Approved by GP';
      case 'sent_to_pharmacy': return 'Sent to Pharmacy';
      case 'dispensed': return 'Dispensed';
      case 'ready_for_collection': return 'Ready for Collection';
      case 'collected': return 'Collected';
      default: return status;
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'urgent': return 'text-red-600';
      case 'emergency': return 'text-red-800 font-bold';
      default: return 'text-gray-600';
    }
  };

  const getTimeAgo = (date) => {
    const now = new Date();
    const requestDate = new Date(date);
    const diffInHours = Math.floor((now - requestDate) / (1000 * 60 * 60));
    
    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${diffInHours} hours ago`;
    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays} days ago`;
  };

  const isStalled = (prescription) => {
    const now = new Date();
    const requestDate = new Date(prescription.requested_at);
    const hoursSinceRequest = (now - requestDate) / (1000 * 60 * 60);
    
    // Consider stalled if pending GP approval for more than 24 hours
    return prescription.status === 'requested' && hoursSinceRequest > 24;
  };

  // Dashboard Overview Stats
  const totalPrescriptions = prescriptions.length;
  const pendingPrescriptions = prescriptions.filter(p => p.status === 'requested').length;
  const readyForCollection = prescriptions.filter(p => p.status === 'ready_for_collection').length;
  const stalledPrescriptions = prescriptions.filter(p => isStalled(p)).length;

  if (!showNewPrescription) {
    return (
      <div className="container mx-auto p-6 max-w-6xl">
        {/* Success Message */}
        {showSuccess && (
          <div className="fixed top-4 right-4 bg-green-500 text-white px-6 py-4 rounded-lg shadow-lg z-50 animate-slide-in">
            <div className="flex items-center">
              <svg className="w-6 h-6 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <div>
                <p className="font-medium">Prescription Request Submitted!</p>
                <p className="text-sm opacity-90">Your GP will review it shortly.</p>
              </div>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-800">Welcome back, {user?.full_name}</h2>
          <p className="text-gray-600 mt-2">Here's an overview of your prescriptions</p>
        </div>

        {/* Dashboard Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Total Prescriptions</p>
                <p className="text-3xl font-bold text-blue-600">{totalPrescriptions}</p>
              </div>
              <div className="bg-blue-100 p-3 rounded-full">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Pending Approval</p>
                <p className="text-3xl font-bold text-yellow-600">{pendingPrescriptions}</p>
              </div>
              <div className="bg-yellow-100 p-3 rounded-full">
                <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Ready for Collection</p>
                <p className="text-3xl font-bold text-green-600">{readyForCollection}</p>
              </div>
              <div className="bg-green-100 p-3 rounded-full">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Needs Attention</p>
                <p className="text-3xl font-bold text-red-600">{stalledPrescriptions}</p>
              </div>
              <div className="bg-red-100 p-3 rounded-full">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200 mb-8">
          <h3 className="text-xl font-semibold text-gray-800 mb-4">Quick Actions</h3>
          <div className="flex flex-wrap gap-4">
            <button
              onClick={() => setShowNewPrescription(true)}
              className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-3 rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all duration-200 shadow-lg flex items-center space-x-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              <span>Request New Prescription</span>
            </button>
            <button
              onClick={() => fetchPrescriptions()}
              className="bg-gray-100 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-200 transition-colors flex items-center space-x-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Recent Prescriptions */}
        <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-semibold text-gray-800">Recent Prescriptions</h3>
            {prescriptions.length > 0 && (
              <span className="text-sm text-gray-500">
                Showing {Math.min(prescriptions.length, 5)} of {prescriptions.length} prescriptions
              </span>
            )}
          </div>
          
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-gray-500 mt-2">Loading prescriptions...</p>
            </div>
          ) : prescriptions.length === 0 ? (
            <div className="text-center py-12">
              <img 
                src="https://images.unsplash.com/photo-1573883430697-4c3479aae6b9?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHxwaGFybWFjeXxlbnwwfHx8Ymx1ZXwxNzUyODE5NjI5fDA&ixlib=rb-4.1.0&q=85"
                alt="No prescriptions"
                className="h-32 w-32 mx-auto mb-4 rounded-full object-cover"
              />
              <h3 className="text-xl font-semibold text-gray-800 mb-2">No Prescriptions Yet</h3>
              <p className="text-gray-600 mb-4">Get started by requesting your first prescription.</p>
              <button
                onClick={() => setShowNewPrescription(true)}
                className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-3 rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all duration-200"
              >
                Request Prescription
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {prescriptions.slice(0, 5).map((prescription) => (
                <div key={prescription.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <h4 className="font-semibold text-gray-800">{prescription.medication_name}</h4>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(prescription.status)}`}>
                        {getStatusText(prescription.status)}
                      </span>
                      {isStalled(prescription) && (
                        <span className="px-2 py-1 bg-red-100 text-red-600 rounded-full text-xs font-medium">
                          Needs Follow-up
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      {prescription.dosage} • {prescription.quantity}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Requested {getTimeAgo(prescription.requested_at)}
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    {prescription.collection_pin && (
                      <div className="text-center">
                        <div className="text-xs text-gray-500">Collection PIN</div>
                        <div className="font-mono font-bold text-blue-600">{prescription.collection_pin}</div>
                      </div>
                    )}
                    <button 
                      onClick={() => setSelectedPrescription(prescription)}
                      className="text-blue-600 hover:text-blue-800 transition-colors"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
              
              {prescriptions.length > 5 && (
                <div className="text-center pt-4">
                  <button
                    onClick={() => {/* Add view all functionality */}}
                    className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                  >
                    View All {prescriptions.length} Prescriptions →
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Prescription Request Form (same as before but with better loading states)
  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="flex items-center mb-6">
        <button
          onClick={() => setShowNewPrescription(false)}
          className="mr-4 text-gray-600 hover:text-gray-800 transition-colors"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h2 className="text-2xl font-bold text-gray-800">Request New Prescription</h2>
      </div>

      <div className="bg-white p-8 rounded-2xl shadow-xl border border-gray-200">
        <form onSubmit={handleCreatePrescription} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Medication Name *
              </label>
              <input
                type="text"
                required
                value={newPrescription.medication_name}
                onChange={(e) => setNewPrescription({...newPrescription, medication_name: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., Amoxicillin"
                disabled={submitLoading}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Dosage *
              </label>
              <input
                type="text"
                required
                value={newPrescription.dosage}
                onChange={(e) => setNewPrescription({...newPrescription, dosage: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., 500mg"
                disabled={submitLoading}
              />
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Quantity *
              </label>
              <input
                type="text"
                required
                value={newPrescription.quantity}
                onChange={(e) => setNewPrescription({...newPrescription, quantity: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., 21 tablets"
                disabled={submitLoading}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Priority
              </label>
              <select
                value={newPrescription.priority}
                onChange={(e) => setNewPrescription({...newPrescription, priority: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={submitLoading}
              >
                <option value="normal">Normal</option>
                <option value="urgent">Urgent</option>
                <option value="emergency">Emergency</option>
              </select>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Instructions *
            </label>
            <input
              type="text"
              required
              value={newPrescription.instructions}
              onChange={(e) => setNewPrescription({...newPrescription, instructions: e.target.value})}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="e.g., Take one tablet three times daily with food"
              disabled={submitLoading}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Additional Notes
            </label>
            <textarea
              value={newPrescription.notes}
              onChange={(e) => setNewPrescription({...newPrescription, notes: e.target.value})}
              rows="3"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Any additional information for your GP..."
              disabled={submitLoading}
            />
          </div>
          
          <div className="flex space-x-4">
            <button
              type="submit"
              disabled={submitLoading}
              className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-8 py-3 rounded-lg hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 font-medium flex items-center"
            >
              {submitLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Submitting...
                </>
              ) : (
                'Submit Request'
              )}
            </button>
            <button
              type="button"
              onClick={() => setShowNewPrescription(false)}
              disabled={submitLoading}
              className="bg-gray-300 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-400 transition-colors font-medium disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const GPDashboard = () => {
  const [prescriptions, setPrescriptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedPrescription, setSelectedPrescription] = useState(null);

  useEffect(() => {
    fetchPrescriptions();
  }, []);

  const fetchPrescriptions = async () => {
    try {
      const response = await axios.get(`${API}/prescriptions`);
      setPrescriptions(response.data);
    } catch (error) {
      console.error('Error fetching prescriptions:', error);
    }
  };

  const handleApprove = async (prescriptionId) => {
    setLoading(true);
    try {
      await axios.put(`${API}/prescriptions/${prescriptionId}`, {
        status: 'gp_approved',
        gp_notes: 'Approved by GP - prescription verified and authorized'
      });
      fetchPrescriptions();
    } catch (error) {
      console.error('Error approving prescription:', error);
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'urgent': return 'text-red-600 bg-red-100';
      case 'emergency': return 'text-red-800 bg-red-200 font-bold';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">GP Dashboard</h2>
        <p className="text-gray-600 mt-2">Review and approve prescription requests from patients</p>
      </div>
      
      <div className="grid gap-6">
        {prescriptions.map((prescription) => (
          <div key={prescription.id} className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200 hover:shadow-xl transition-all duration-200">
            <div className="flex justify-between items-start mb-4">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <h3 className="text-xl font-semibold text-gray-800">
                    {prescription.medication_name}
                  </h3>
                  {prescription.priority !== 'normal' && (
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getPriorityColor(prescription.priority)}`}>
                      {prescription.priority.toUpperCase()}
                    </span>
                  )}
                </div>
                <div className="text-gray-600 space-y-1">
                  <p><strong>Patient:</strong> {prescription.patient_nhs_number ? `NHS: ${prescription.patient_nhs_number}` : 'Patient ID: ' + prescription.patient_id}</p>
                  <p><strong>Dosage:</strong> {prescription.dosage}</p>
                  <p><strong>Quantity:</strong> {prescription.quantity}</p>
                  <p><strong>Instructions:</strong> {prescription.instructions}</p>
                </div>
              </div>
              
              <div className="ml-4">
                <button
                  onClick={() => handleApprove(prescription.id)}
                  disabled={loading}
                  className="bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-3 rounded-lg hover:from-green-700 hover:to-green-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 font-medium shadow-lg"
                >
                  {loading ? 'Approving...' : 'Approve Prescription'}
                </button>
              </div>
            </div>
            
            {prescription.notes && (
              <div className="bg-blue-50 p-4 rounded-lg mb-4">
                <p className="text-sm text-blue-800">
                  <strong>Patient Notes:</strong> {prescription.notes}
                </p>
              </div>
            )}
            
            <div className="flex justify-between items-center text-sm text-gray-500 border-t pt-4">
              <div>
                <p>Requested: {new Date(prescription.requested_at).toLocaleString()}</p>
                <p>Type: {prescription.prescription_type}</p>
              </div>
              {prescription.priority !== 'normal' && (
                <div className="text-right">
                  <p className="font-medium text-red-600">⚠️ Priority: {prescription.priority}</p>
                </div>
              )}
            </div>
          </div>
        ))}
        
        {prescriptions.length === 0 && (
          <div className="text-center py-12">
            <img 
              src="https://images.unsplash.com/photo-1600091474842-83bb9c05a723?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDJ8MHwxfHNlYXJjaHwzfHxtZWRpY2FsJTIwcHJlc2NyaXB0aW9ufGVufDB8fHxibHVlfDE3NTI4MTk2MTR8MA&ixlib=rb-4.1.0&q=85"
              alt="No prescriptions"
              className="h-32 w-32 mx-auto mb-4 rounded-full object-cover"
            />
            <h3 className="text-xl font-semibold text-gray-800 mb-2">No Pending Prescriptions</h3>
            <p className="text-gray-600">All prescription requests have been reviewed. New requests will appear here.</p>
          </div>
        )}
      </div>
    </div>
  );
};

const PharmacyDashboard = () => {
  const [prescriptions, setPrescriptions] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchPrescriptions();
  }, []);

  const fetchPrescriptions = async () => {
    try {
      const response = await axios.get(`${API}/prescriptions`);
      setPrescriptions(response.data);
    } catch (error) {
      console.error('Error fetching prescriptions:', error);
    }
  };

  const handleFulfill = async (prescriptionId) => {
    setLoading(true);
    try {
      await axios.put(`${API}/prescriptions/${prescriptionId}`, {
        status: 'dispensed',
        pharmacy_notes: 'Prescription dispensed and ready for collection'
      });
      fetchPrescriptions();
    } catch (error) {
      console.error('Error fulfilling prescription:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Pharmacy Dashboard</h2>
        <p className="text-gray-600 mt-2">Manage approved prescriptions and dispensing</p>
      </div>
      
      <div className="grid gap-6">
        {prescriptions.map((prescription) => (
          <div key={prescription.id} className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200 hover:shadow-xl transition-all duration-200">
            <div className="flex justify-between items-start mb-4">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <h3 className="text-xl font-semibold text-gray-800">
                    {prescription.medication_name}
                  </h3>
                  <span className="px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 border border-blue-300">
                    GP Approved
                  </span>
                </div>
                <div className="text-gray-600 space-y-1">
                  <p><strong>Patient:</strong> {prescription.patient_nhs_number ? `NHS: ${prescription.patient_nhs_number}` : 'Patient ID: ' + prescription.patient_id}</p>
                  <p><strong>Dosage:</strong> {prescription.dosage}</p>
                  <p><strong>Quantity:</strong> {prescription.quantity}</p>
                  <p><strong>Instructions:</strong> {prescription.instructions}</p>
                </div>
              </div>
              
              <div className="ml-4">
                <button
                  onClick={() => handleFulfill(prescription.id)}
                  disabled={loading}
                  className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-3 rounded-lg hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 font-medium shadow-lg"
                >
                  {loading ? 'Dispensing...' : 'Mark as Dispensed'}
                </button>
              </div>
            </div>
            
            {prescription.gp_notes && (
              <div className="bg-green-50 p-4 rounded-lg mb-4">
                <p className="text-sm text-green-800">
                  <strong>GP Notes:</strong> {prescription.gp_notes}
                </p>
              </div>
            )}
            
            <div className="flex justify-between items-center text-sm text-gray-500 border-t pt-4">
              <div>
                <p>Approved: {new Date(prescription.approved_at).toLocaleString()}</p>
                <p>Collection PIN: <span className="font-medium text-blue-600">{prescription.collection_pin}</span></p>
              </div>
              <div className="text-right">
                <p>Type: {prescription.prescription_type}</p>
              </div>
            </div>
          </div>
        ))}
        
        {prescriptions.length === 0 && (
          <div className="text-center py-12">
            <img 
              src="https://images.unsplash.com/photo-1573883430697-4c3479aae6b9?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHxwaGFybWFjeXxlbnwwfHx8Ymx1ZXwxNzUyODE5NjI5fDA&ixlib=rb-4.1.0&q=85"
              alt="No prescriptions"
              className="h-32 w-32 mx-auto mb-4 rounded-full object-cover"
            />
            <h3 className="text-xl font-semibold text-gray-800 mb-2">No Approved Prescriptions</h3>
            <p className="text-gray-600">Approved prescriptions will appear here for dispensing.</p>
          </div>
        )}
      </div>
    </div>
  );
};

const DelegateDashboard = () => {
  const [delegations, setDelegations] = useState([]);
  const [prescriptions, setPrescriptions] = useState([]);

  useEffect(() => {
    fetchDelegations();
    fetchPrescriptions();
  }, []);

  const fetchDelegations = async () => {
    try {
      const response = await axios.get(`${API}/delegations`);
      setDelegations(response.data);
    } catch (error) {
      console.error('Error fetching delegations:', error);
    }
  };

  const fetchPrescriptions = async () => {
    try {
      const response = await axios.get(`${API}/prescriptions`);
      setPrescriptions(response.data);
    } catch (error) {
      console.error('Error fetching prescriptions:', error);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-800">Delegate Dashboard</h2>
        <p className="text-gray-600 mt-2">Manage authorized prescription collections</p>
      </div>
      
      <div className="grid gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200">
          <h3 className="text-xl font-semibold text-gray-800 mb-4">Authorization Status</h3>
          <div className="bg-blue-50 p-4 rounded-lg">
            <p className="text-blue-800">
              🔒 Delegate features are being enhanced to support secure prescription collection with proper authorization and audit trails.
            </p>
            <p className="text-blue-700 mt-2">
              Features coming soon:
            </p>
            <ul className="list-disc list-inside text-blue-700 mt-2 space-y-1">
              <li>QR code scanning for prescription collection</li>
              <li>PIN-based authorization system</li>
              <li>Real-time collection notifications</li>
              <li>Audit logs for CQC compliance</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

const Dashboard = () => {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  const renderDashboard = () => {
    switch (user.role) {
      case 'patient':
        return <PatientDashboard />;
      case 'gp':
        return <GPDashboard />;
      case 'pharmacy':
        return <PharmacyDashboard />;
      case 'delegate':
        return <DelegateDashboard />;
      default:
        return (
          <div className="container mx-auto p-6 text-center">
            <h2 className="text-2xl font-bold text-gray-800">Invalid Role</h2>
            <p className="text-gray-600 mt-2">Please contact support for assistance.</p>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="pb-8">
        {renderDashboard()}
      </main>
    </div>
  );
};

function App() {
  const { token } = useAuth();

  return (
    <div className="App">
      {token ? <Dashboard /> : <LoginForm />}
    </div>
  );
}

export default function AppWithAuth() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}