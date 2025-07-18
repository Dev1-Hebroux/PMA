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

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchCurrentUser();
    }
  }, [token]);

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get(`${API}/users/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching user:', error);
      logout();
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
      return { success: false, error: error.response?.data?.detail || 'Login failed' };
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
      return { success: false, error: error.response?.data?.detail || 'Registration failed' };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, token }}>
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
  const { user, logout } = useAuth();

  return (
    <header className="bg-blue-600 text-white p-4">
      <div className="container mx-auto flex justify-between items-center">
        <h1 className="text-2xl font-bold">MedRx Manager</h1>
        {user && (
          <div className="flex items-center space-x-4">
            <span className="text-sm">
              {user.full_name} ({user.role})
            </span>
            <button
              onClick={logout}
              className="bg-red-500 hover:bg-red-600 px-3 py-1 rounded text-sm"
            >
              Logout
            </button>
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
    phone: '',
    address: ''
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
        result = await register(formData);
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
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <div className="text-center mb-6">
          <img 
            src="https://images.unsplash.com/photo-1619278874214-7eb5d1b7498a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDJ8MHwxfHNlYXJjaHwxfHxtZWRpY2FsJTIwcHJlc2NyaXB0aW9ufGVufDB8fHxibHVlfDE3NTI4MTk2MTR8MA&ixlib=rb-4.1.0&q=85"
            alt="Medical"
            className="h-20 w-20 mx-auto mb-4 rounded-full object-cover"
          />
          <h2 className="text-2xl font-bold text-gray-800">
            {isLogin ? 'Sign In' : 'Sign Up'}
          </h2>
          <p className="text-gray-600 mt-2">
            {isLogin ? 'Welcome back to MedRx Manager' : 'Create your MedRx Manager account'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
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
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Role
                </label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="patient">Patient</option>
                  <option value="gp">GP (Doctor)</option>
                  <option value="pharmacy">Pharmacy</option>
                  <option value="delegate">Delegate/Carer</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Phone (Optional)
                </label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({...formData, phone: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </>
          )}

          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? 'Processing...' : (isLogin ? 'Sign In' : 'Sign Up')}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-blue-600 hover:text-blue-800"
          >
            {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
};

const PatientDashboard = () => {
  const [prescriptions, setPrescriptions] = useState([]);
  const [showNewPrescription, setShowNewPrescription] = useState(false);
  const [newPrescription, setNewPrescription] = useState({
    medication_name: '',
    dosage: '',
    quantity: '',
    instructions: '',
    notes: ''
  });
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

  const handleCreatePrescription = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/prescriptions`, newPrescription);
      setNewPrescription({
        medication_name: '',
        dosage: '',
        quantity: '',
        instructions: '',
        notes: ''
      });
      setShowNewPrescription(false);
      fetchPrescriptions();
    } catch (error) {
      console.error('Error creating prescription:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'requested': return 'bg-yellow-100 text-yellow-800';
      case 'gp_approved': return 'bg-blue-100 text-blue-800';
      case 'pharmacy_fulfilled': return 'bg-green-100 text-green-800';
      case 'collected': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'requested': return 'Pending GP Approval';
      case 'gp_approved': return 'Ready for Pharmacy';
      case 'pharmacy_fulfilled': return 'Ready for Collection';
      case 'collected': return 'Collected';
      default: return status;
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">My Prescriptions</h2>
        <button
          onClick={() => setShowNewPrescription(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
        >
          New Prescription Request
        </button>
      </div>

      {showNewPrescription && (
        <div className="bg-white p-6 rounded-lg shadow-md mb-6">
          <h3 className="text-lg font-semibold mb-4">Request New Prescription</h3>
          <form onSubmit={handleCreatePrescription} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Medication Name
                </label>
                <input
                  type="text"
                  required
                  value={newPrescription.medication_name}
                  onChange={(e) => setNewPrescription({...newPrescription, medication_name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Dosage
                </label>
                <input
                  type="text"
                  required
                  value={newPrescription.dosage}
                  onChange={(e) => setNewPrescription({...newPrescription, dosage: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Quantity
                </label>
                <input
                  type="text"
                  required
                  value={newPrescription.quantity}
                  onChange={(e) => setNewPrescription({...newPrescription, quantity: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Instructions
                </label>
                <input
                  type="text"
                  required
                  value={newPrescription.instructions}
                  onChange={(e) => setNewPrescription({...newPrescription, instructions: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Notes (Optional)
              </label>
              <textarea
                value={newPrescription.notes}
                onChange={(e) => setNewPrescription({...newPrescription, notes: e.target.value})}
                rows="3"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex space-x-4">
              <button
                type="submit"
                disabled={loading}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Submitting...' : 'Submit Request'}
              </button>
              <button
                type="button"
                onClick={() => setShowNewPrescription(false)}
                className="bg-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="grid gap-4">
        {prescriptions.map((prescription) => (
          <div key={prescription.id} className="bg-white p-6 rounded-lg shadow-md">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">
                  {prescription.medication_name}
                </h3>
                <p className="text-gray-600">
                  {prescription.dosage} • {prescription.quantity}
                </p>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(prescription.status)}`}>
                {getStatusText(prescription.status)}
              </span>
            </div>
            <p className="text-gray-700 mb-2">
              <strong>Instructions:</strong> {prescription.instructions}
            </p>
            {prescription.notes && (
              <p className="text-gray-600 mb-2">
                <strong>Notes:</strong> {prescription.notes}
              </p>
            )}
            <p className="text-sm text-gray-500">
              Requested: {new Date(prescription.requested_at).toLocaleDateString()}
            </p>
          </div>
        ))}
        {prescriptions.length === 0 && (
          <div className="text-center py-12">
            <img 
              src="https://images.unsplash.com/photo-1573883430697-4c3479aae6b9?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHxwaGFybWFjeXxlbnwwfHx8Ymx1ZXwxNzUyODE5NjI5fDA&ixlib=rb-4.1.0&q=85"
              alt="No prescriptions"
              className="h-32 w-32 mx-auto mb-4 rounded-full object-cover"
            />
            <p className="text-gray-500">No prescriptions yet. Click "New Prescription Request" to get started.</p>
          </div>
        )}
      </div>
    </div>
  );
};

const GPDashboard = () => {
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

  const handleApprove = async (prescriptionId) => {
    setLoading(true);
    try {
      await axios.put(`${API}/prescriptions/${prescriptionId}`, {
        status: 'gp_approved',
        gp_notes: 'Approved by GP'
      });
      fetchPrescriptions();
    } catch (error) {
      console.error('Error approving prescription:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Pending Prescriptions</h2>
      
      <div className="grid gap-4">
        {prescriptions.map((prescription) => (
          <div key={prescription.id} className="bg-white p-6 rounded-lg shadow-md">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">
                  {prescription.medication_name}
                </h3>
                <p className="text-gray-600">
                  {prescription.dosage} • {prescription.quantity}
                </p>
              </div>
              <button
                onClick={() => handleApprove(prescription.id)}
                disabled={loading}
                className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {loading ? 'Approving...' : 'Approve'}
              </button>
            </div>
            <p className="text-gray-700 mb-2">
              <strong>Instructions:</strong> {prescription.instructions}
            </p>
            {prescription.notes && (
              <p className="text-gray-600 mb-2">
                <strong>Patient Notes:</strong> {prescription.notes}
              </p>
            )}
            <p className="text-sm text-gray-500">
              Requested: {new Date(prescription.requested_at).toLocaleDateString()}
            </p>
          </div>
        ))}
        {prescriptions.length === 0 && (
          <div className="text-center py-12">
            <img 
              src="https://images.unsplash.com/photo-1600091474842-83bb9c05a723?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDJ8MHwxfHNlYXJjaHwzfHxtZWRpY2FsJTIwcHJlc2NyaXB0aW9ufGVufDB8fHxibHVlfDE3NTI4MTk2MTR8MA&ixlib=rb-4.1.0&q=85"
              alt="No prescriptions"
              className="h-32 w-32 mx-auto mb-4 rounded-full object-cover"
            />
            <p className="text-gray-500">No pending prescriptions to review.</p>
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
        status: 'pharmacy_fulfilled',
        pharmacy_notes: 'Fulfilled by pharmacy'
      });
      fetchPrescriptions();
    } catch (error) {
      console.error('Error fulfilling prescription:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Approved Prescriptions</h2>
      
      <div className="grid gap-4">
        {prescriptions.map((prescription) => (
          <div key={prescription.id} className="bg-white p-6 rounded-lg shadow-md">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">
                  {prescription.medication_name}
                </h3>
                <p className="text-gray-600">
                  {prescription.dosage} • {prescription.quantity}
                </p>
              </div>
              <button
                onClick={() => handleFulfill(prescription.id)}
                disabled={loading}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Fulfilling...' : 'Mark as Fulfilled'}
              </button>
            </div>
            <p className="text-gray-700 mb-2">
              <strong>Instructions:</strong> {prescription.instructions}
            </p>
            {prescription.gp_notes && (
              <p className="text-gray-600 mb-2">
                <strong>GP Notes:</strong> {prescription.gp_notes}
              </p>
            )}
            <p className="text-sm text-gray-500">
              Approved: {new Date(prescription.approved_at).toLocaleDateString()}
            </p>
          </div>
        ))}
        {prescriptions.length === 0 && (
          <div className="text-center py-12">
            <img 
              src="https://images.unsplash.com/photo-1573883430697-4c3479aae6b9?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHxwaGFybWFjeXxlbnwwfHx8Ymx1ZXwxNzUyODE5NjI5fDA&ixlib=rb-4.1.0&q=85"
              alt="No prescriptions"
              className="h-32 w-32 mx-auto mb-4 rounded-full object-cover"
            />
            <p className="text-gray-500">No approved prescriptions to fulfill.</p>
          </div>
        )}
      </div>
    </div>
  );
};

const DelegateDashboard = () => {
  return (
    <div className="container mx-auto p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Delegate Dashboard</h2>
      <div className="bg-white p-6 rounded-lg shadow-md">
        <p className="text-gray-600">
          Delegate features coming soon. This will allow authorized family members and carers to collect prescriptions on behalf of patients.
        </p>
      </div>
    </div>
  );
};

const Dashboard = () => {
  const { user } = useAuth();

  if (!user) {
    return <div>Loading...</div>;
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
        return <div>Invalid role</div>;
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Header />
      {renderDashboard()}
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