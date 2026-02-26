import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Button } from './ui/button';
import { Sheet, SheetContent, SheetTrigger } from './ui/sheet';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from './ui/dropdown-menu';
import { Menu, User, Heart, Calendar, LogOut, Settings, LayoutDashboard, ChevronDown } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const Navbar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();

  const isActive = (path) => location.pathname === path;

  const navLinks = [
    { path: '/', label: 'Home' },
    { path: '/adventures', label: 'Adventures' },
    { path: '/about', label: 'About' }
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const getDashboardLink = () => {
    if (!user) return '/client/dashboard';
    switch (user.role) {
      case 'admin': return '/admin/dashboard';
      case 'webdev': return '/admin/dashboard';
      case 'host': return '/host/dashboard';
      default: return '/client/dashboard';
    }
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center group" data-testid="nav-logo">
            <img 
              src="/seeker-logo-transparent.png" 
              alt="Seeker Adventure" 
              className="h-9 sm:h-10 md:h-12 w-auto object-contain transform group-hover:scale-105 transition-transform duration-200"
              style={{ imageRendering: 'auto' }}
            />
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-1">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                data-testid={`nav-${link.label.toLowerCase()}`}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200 ${
                  isActive(link.path)
                    ? 'bg-pink-50 text-[#EB5A7E]'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Desktop Actions */}
          <div className="hidden md:flex items-center space-x-3">
            <Link to="/wishlist" data-testid="nav-wishlist">
              <Button variant="ghost" size="icon" className="relative hover:bg-gray-100">
                <Heart className="w-5 h-5" />
              </Button>
            </Link>
            <Link to="/bookings" data-testid="nav-bookings">
              <Button variant="ghost" size="icon" className="hover:bg-gray-100">
                <Calendar className="w-5 h-5" />
              </Button>
            </Link>
            
            {isAuthenticated && user ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="flex items-center gap-2" data-testid="nav-user-menu">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#EB5A7E] to-[#F5A623] flex items-center justify-center overflow-hidden">
                      {user.avatar ? (
                        <img src={user.avatar} alt={user.name} className="w-full h-full object-cover" />
                      ) : (
                        <User className="w-4 h-4 text-white" />
                      )}
                    </div>
                    <span className="text-sm font-medium max-w-[100px] truncate">{user.name}</span>
                    <ChevronDown className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <div className="px-2 py-1.5">
                    <p className="text-sm font-medium">{user.name}</p>
                    <p className="text-xs text-gray-500">{user.email}</p>
                    <p className="text-xs text-[#5ABFBB] font-medium">{user.client_id}</p>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link to={getDashboardLink()} className="flex items-center cursor-pointer">
                      <LayoutDashboard className="w-4 h-4 mr-2" />
                      Dashboard
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to="/profile" className="flex items-center cursor-pointer">
                      <Settings className="w-4 h-4 mr-2" />
                      Profile Settings
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="text-red-600 cursor-pointer">
                    <LogOut className="w-4 h-4 mr-2" />
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <Link to="/profile" data-testid="nav-signin">
                <Button className="bg-gradient-to-r from-[#EB5A7E] to-[#F5A623] hover:from-[#D64566] hover:to-[#E09316] text-white shadow-md">
                  <User className="w-4 h-4 mr-2" />
                  Sign In
                </Button>
              </Link>
            )}
          </div>

          {/* Mobile Menu */}
          <Sheet open={isOpen} onOpenChange={setIsOpen}>
            <SheetTrigger asChild className="md:hidden">
              <Button variant="ghost" size="icon" data-testid="nav-mobile-menu">
                <Menu className="w-6 h-6" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[300px] sm:w-[400px]">
              <div className="flex flex-col space-y-4 mt-8">
                <img src="/seeker-logo-transparent.png" alt="Seeker Adventure" className="h-12 w-auto object-contain mb-4" style={{ imageRendering: 'auto' }} />
                
                {isAuthenticated && user && (
                  <div className="p-4 bg-gray-50 rounded-lg mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#EB5A7E] to-[#F5A623] flex items-center justify-center overflow-hidden">
                        {user.avatar ? (
                          <img src={user.avatar} alt={user.name} className="w-full h-full object-cover" />
                        ) : (
                          <User className="w-6 h-6 text-white" />
                        )}
                      </div>
                      <div>
                        <p className="font-medium">{user.name}</p>
                        <p className="text-xs text-[#5ABFBB]">{user.client_id}</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {navLinks.map((link) => (
                  <Link
                    key={link.path}
                    to={link.path}
                    onClick={() => setIsOpen(false)}
                    className={`px-4 py-3 rounded-lg text-base font-medium transition-colors ${
                      isActive(link.path)
                        ? 'bg-pink-50 text-[#EB5A7E]'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    {link.label}
                  </Link>
                ))}
                <div className="border-t pt-4 space-y-2">
                  {isAuthenticated && (
                    <Link to={getDashboardLink()} onClick={() => setIsOpen(false)}>
                      <Button variant="outline" className="w-full justify-start">
                        <LayoutDashboard className="w-4 h-4 mr-2" />
                        Dashboard
                      </Button>
                    </Link>
                  )}
                  <Link to="/wishlist" onClick={() => setIsOpen(false)}>
                    <Button variant="outline" className="w-full justify-start">
                      <Heart className="w-4 h-4 mr-2" />
                      Wishlist
                    </Button>
                  </Link>
                  <Link to="/bookings" onClick={() => setIsOpen(false)}>
                    <Button variant="outline" className="w-full justify-start">
                      <Calendar className="w-4 h-4 mr-2" />
                      My Bookings
                    </Button>
                  </Link>
                  
                  {isAuthenticated ? (
                    <>
                      <Link to="/profile" onClick={() => setIsOpen(false)}>
                        <Button variant="outline" className="w-full justify-start">
                          <Settings className="w-4 h-4 mr-2" />
                          Profile Settings
                        </Button>
                      </Link>
                      <Button 
                        variant="outline" 
                        className="w-full justify-start text-red-600 border-red-200 hover:bg-red-50"
                        onClick={() => { handleLogout(); setIsOpen(false); }}
                      >
                        <LogOut className="w-4 h-4 mr-2" />
                        Logout
                      </Button>
                    </>
                  ) : (
                    <Link to="/profile" onClick={() => setIsOpen(false)}>
                      <Button className="w-full bg-gradient-to-r from-[#EB5A7E] to-[#F5A623] hover:from-[#D64566] hover:to-[#E09316] text-white">
                        <User className="w-4 h-4 mr-2" />
                        Sign In
                      </Button>
                    </Link>
                  )}
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
