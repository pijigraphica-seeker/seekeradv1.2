import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import { Toaster } from './components/ui/sonner';
import Home from './pages/Home';
import Adventures from './pages/Adventures';
import TripDetail from './pages/TripDetail';
import Bookings from './pages/Bookings';
import Wishlist from './pages/Wishlist';
import Profile from './pages/Profile';
import About from './pages/About';
import ClientDashboard from './pages/ClientDashboard';
import HostDashboard from './pages/HostDashboard';
import AdminDashboard from './pages/AdminDashboard';
import AuthCallback from './pages/AuthCallback';
import TermsConditions from './pages/TermsConditions';
import BecomeHost from './pages/BecomeHost';
import ResetPassword from './pages/ResetPassword';

// Router component that handles auth callback detection
function AppRouter() {
  const location = useLocation();
  
  // Check URL fragment for session_id (OAuth callback)
  // CRITICAL: This must be checked synchronously during render to prevent race conditions
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/adventures" element={<Adventures />} />
        <Route path="/trip/:id" element={<TripDetail />} />
        <Route path="/trip/:activity/:slug" element={<TripDetail />} />
        <Route path="/bookings" element={<Bookings />} />
        <Route path="/bookings/:bookingId" element={<Bookings />} />
        <Route path="/wishlist" element={<Wishlist />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/about" element={<About />} />
        <Route path="/terms" element={<TermsConditions />} />
        <Route path="/become-host" element={<BecomeHost />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        
        {/* Auth callback route */}
        <Route path="/auth/callback" element={<AuthCallback />} />
        
        {/* Dashboard Routes */}
        <Route path="/client/dashboard" element={<ClientDashboard />} />
        <Route path="/host/dashboard" element={<HostDashboard />} />
        <Route path="/admin/dashboard" element={<AdminDashboard />} />
      </Routes>
      <Footer />
    </>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
