import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  ListTodo,
  Settings,
  AlertTriangle,
  Plus,
  Calendar,
  Activity,
  History,
  User as UserIcon,
  Key
} from 'lucide-react';
import axios from 'axios';
import Dashboard from './components/Dashboard';
import TaskManager from './components/TaskManager';
import LBSCalendar from './components/LBSCalendar';

const SidebarItem = ({ icon: Icon, label, active, onClick }) => (
  <div
    onClick={onClick}
    className={`flex items-center gap-4 p-4 cursor-pointer transition-all ${active ? 'bg-white/10 text-white rounded-xl' : 'text-slate-400 hover:text-white hover:bg-white/5 rounded-xl'
      }`}
  >
    <Icon size={20} />
    <span className="font-medium">{label}</span>
  </div>
);

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [apiKey, setApiKey] = useState(localStorage.getItem('lbs_api_key') || '');
  const [isAuthOpen, setIsAuthOpen] = useState(!apiKey);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);

  // Registration Form State
  const [regData, setRegData] = useState({ name: '', email: '' });
  const [regError, setRegError] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);

  useEffect(() => {
    localStorage.setItem('lbs_api_key', apiKey);
  }, [apiKey]);

  const handleRegister = async (e) => {
    e.preventDefault();
    setIsRegistering(true);
    setRegError('');
    try {
      const resp = await axios.post(`${import.meta.env.VITE_API_BASE_URL || '/api/lbs'}/users/`, regData);
      const newKey = resp.data.api_key;
      setApiKey(newKey);
      setIsRegisterOpen(false);
      setIsAuthOpen(false);
      alert("Registration successful! Your API key has been set automatically.");
    } catch (err) {
      setRegError(err.response?.data?.detail || err.message);
    } finally {
      setIsRegistering(false);
    }
  };

  return (
    <div className="flex h-screen bg-[#0a0a0c]">
      {/* Sidebar */}
      <div className="w-64 border-r border-white/5 p-6 flex flex-col gap-8">
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center font-bold text-white">L</div>
          <h1 className="text-xl font-bold gradient-text">LBS Control</h1>
        </div>

        <nav className="flex flex-col gap-2 flex-grow">
          <SidebarItem
            icon={LayoutDashboard}
            label="Dashboard"
            active={activeTab === 'dashboard'}
            onClick={() => setActiveTab('dashboard')}
          />
          <SidebarItem
            icon={ListTodo}
            label="Tasks"
            active={activeTab === 'tasks'}
            onClick={() => setActiveTab('tasks')}
          />
          <SidebarItem
            icon={Calendar}
            label="Calendar"
            active={activeTab === 'calendar'}
            onClick={() => setActiveTab('calendar')}
          />
          <SidebarItem
            icon={Settings}
            label="Settings"
            active={activeTab === 'settings'}
            onClick={() => setActiveTab('settings')}
          />
        </nav>

        <div
          onClick={() => setIsAuthOpen(true)}
          className="p-4 glass-card flex flex-col gap-2 cursor-pointer hover:border-white/20 transition-all"
        >
          <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Authentication</div>
          <div className="flex items-center gap-2 text-xs text-slate-300">
            <Key size={12} />
            <span className="truncate">{apiKey ? '••••' + apiKey.slice(-4) : 'Set API Key'}</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-grow overflow-y-auto p-10">
        {activeTab === 'dashboard' && <Dashboard apiKey={apiKey} />}
        {activeTab === 'tasks' && <TaskManager apiKey={apiKey} />}
        {activeTab === 'calendar' && <LBSCalendar apiKey={apiKey} />}
        {activeTab === 'settings' && (
          <div className="max-w-2xl mx-auto">
            <h2 className="text-2xl font-bold mb-8">System Configuration</h2>
            <div className="glass-card p-6 flex flex-col gap-6">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Microservice Endpoint</label>
                <input className="w-full" disabled value={`${import.meta.env.VITE_API_BASE_URL || '/api/lbs'}`} />
              </div>
              <div className="p-4 bg-purple-500/10 border border-purple-500/20 rounded-xl text-sm text-purple-200">
                Default configurations (ALPHA, BETA, CAP) are loaded from the backend per user session.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Auth Modal */}
      {isAuthOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="glass-card p-8 w-[400px] flex flex-col gap-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">LBS Authentication</h2>
              <button onClick={() => setIsAuthOpen(false)} className="text-slate-500 hover:text-white">&times;</button>
            </div>
            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">X-API-Key</label>
                <input
                  className="w-full"
                  placeholder="Enter API Key"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
              </div>
            </div>
            <button className="primary w-full mt-2" onClick={() => setIsAuthOpen(false)}>Access Manager</button>

            <div className="text-center py-2">
              <span className="text-xs text-slate-500">Don't have a key? </span>
              <button
                onClick={() => { setIsAuthOpen(false); setIsRegisterOpen(true); }}
                className="text-xs text-blue-400 hover:underline font-bold"
              >
                Create Account
              </button>
            </div>

            <p className="text-[10px] text-slate-500 text-center">
              Keys are stored locally in your browser.
            </p>
          </div>
        </div>
      )}

      {/* Register Modal */}
      {isRegisterOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
          <form onSubmit={handleRegister} className="glass-card p-8 w-[400px] flex flex-col gap-6">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">Create LBS Account</h2>
              <button type="button" onClick={() => setIsRegisterOpen(false)} className="text-slate-500 hover:text-white">&times;</button>
            </div>

            {regError && <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg">{regError}</div>}

            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Full Name</label>
                <input
                  required
                  className="w-full"
                  placeholder="e.g. John Doe"
                  value={regData.name}
                  onChange={(e) => setRegData({ ...regData, name: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Email Address</label>
                <input
                  required
                  type="email"
                  className="w-full"
                  placeholder="name@example.com"
                  value={regData.email}
                  onChange={(e) => setRegData({ ...regData, email: e.target.value })}
                />
              </div>
            </div>

            <button type="submit" disabled={isRegistering} className="primary w-full mt-2">
              {isRegistering ? 'Creating Account...' : 'Generate API Key'}
            </button>

            <div className="text-center">
              <button
                type="button"
                onClick={() => { setIsRegisterOpen(false); setIsAuthOpen(true); }}
                className="text-xs text-slate-500 hover:text-white"
              >
                Back to Login
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default App;
