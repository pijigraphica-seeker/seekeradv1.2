import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const ScrollLink = ({ to, children, className }) => {
  const navigate = useNavigate();
  return (
    <a href={to} className={className} onClick={(e) => { e.preventDefault(); navigate(to); window.scrollTo(0, 0); }}>
      {children}
    </a>
  );
};
import { Facebook, Instagram, Mail, Phone, MapPin, UserPlus } from 'lucide-react';
import { contentAPI } from '../services/api';

const Footer = () => {
  const currentYear = new Date().getFullYear();
  const [c, setC] = useState(null);

  useEffect(() => {
    contentAPI.getSection('footer').then(setC).catch(() => {});
  }, []);

  const desc = c?.company_description || 'Your trusted partner for unforgettable adventure travel experiences across Indonesia.';
  const phone = c?.phone_1 || '+60 11-7000 1232';
  const email = c?.email || 'sales@seekeradventure.com';
  const location = c?.location || 'Indonesia';
  const whatsapp = c?.whatsapp || '601170001232';
  const fbUrl = c?.facebook_url || 'https://facebook.com/seekeradventure';
  const igUrl = c?.instagram_url || 'https://instagram.com/seekeradventure_';

  return (
    <footer className="bg-gray-900 text-gray-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Brand Section */}
          <div className="md:col-span-1">
            <Link to="/" className="inline-block mb-4">
              <img
                src="/seeker-logo-transparent.png"
                alt="Seeker Adventure"
                className="h-10 sm:h-12 md:h-14 w-auto object-contain"
                style={{ imageRendering: 'auto' }}
              />
            </Link>
            <p className="text-sm text-gray-400 mb-4">{desc}</p>
            {/* Social Links */}
            <div className="flex space-x-3">
              <a href={fbUrl} target="_blank" rel="noopener noreferrer" className="w-9 h-9 bg-gray-800 hover:bg-[#EB5A7E] rounded-full flex items-center justify-center transition-colors">
                <Facebook className="w-4 h-4" />
              </a>
              <a href={igUrl} target="_blank" rel="noopener noreferrer" className="w-9 h-9 bg-gray-800 hover:bg-[#F5A623] rounded-full flex items-center justify-center transition-colors">
                <Instagram className="w-4 h-4" />
              </a>
              <a href={`https://wa.me/${whatsapp}`} target="_blank" rel="noopener noreferrer" className="w-9 h-9 bg-gray-800 hover:bg-green-500 rounded-full flex items-center justify-center transition-colors">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                </svg>
              </a>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-white font-semibold mb-4">Quick Links</h3>
            <ul className="space-y-2">
              <li><ScrollLink to="/adventures" className="hover:text-[#EB5A7E] transition-colors text-sm">All Adventures</ScrollLink></li>
              <li><ScrollLink to="/about" className="hover:text-[#EB5A7E] transition-colors text-sm">About Us</ScrollLink></li>
              <li><ScrollLink to="/bookings" className="hover:text-[#EB5A7E] transition-colors text-sm">My Bookings</ScrollLink></li>
              <li><ScrollLink to="/wishlist" className="hover:text-[#EB5A7E] transition-colors text-sm">Wishlist</ScrollLink></li>
            </ul>
          </div>

          {/* Adventure Types */}
          <div>
            <h3 className="text-white font-semibold mb-4">Adventure Types</h3>
            <ul className="space-y-2">
              <li><ScrollLink to="/adventures?activity=hiking" className="hover:text-[#F5A623] transition-colors text-sm">Hiking</ScrollLink></li>
              <li><ScrollLink to="/adventures?activity=camping" className="hover:text-[#F5A623] transition-colors text-sm">Camping</ScrollLink></li>
              <li><ScrollLink to="/adventures?activity=diving" className="hover:text-[#5ABFBB] transition-colors text-sm">Diving</ScrollLink></li>
              <li><ScrollLink to="/adventures?activity=kayaking" className="hover:text-[#5ABFBB] transition-colors text-sm">Kayaking</ScrollLink></li>
            </ul>
          </div>

          {/* Contact Info */}
          <div>
            <h3 className="text-white font-semibold mb-4">Contact Us</h3>
            <ul className="space-y-3">
              <li>
                <a href={`https://wa.me/${whatsapp}`} target="_blank" rel="noopener noreferrer" className="flex items-center hover:text-green-400 transition-colors text-sm">
                  <svg className="w-4 h-4 mr-2 flex-shrink-0 text-green-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                  </svg>
                  {phone}
                </a>
              </li>
              <li className="flex items-start">
                <Phone className="w-4 h-4 mr-2 mt-1 flex-shrink-0 text-[#5ABFBB]" />
                <a href={`tel:${phone.replace(/\s/g, '')}`} className="hover:text-[#EB5A7E] transition-colors text-sm">{phone}</a>
              </li>
              <li className="flex items-start">
                <Mail className="w-4 h-4 mr-2 mt-1 flex-shrink-0 text-[#5ABFBB]" />
                <a href={`mailto:${email}`} className="hover:text-[#EB5A7E] transition-colors text-sm">{email}</a>
              </li>
              <li className="flex items-start">
                <MapPin className="w-4 h-4 mr-2 mt-1 flex-shrink-0 text-[#5ABFBB]" />
                <div className="text-sm">{location}</div>
              </li>
            </ul>
          </div>
        </div>

        {/* Become a Host CTA */}
        <div className="mb-8 p-6 rounded-2xl bg-gray-800 border border-gray-700">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[#EB5A7E]/20 flex items-center justify-center">
                <UserPlus className="w-5 h-5 text-[#EB5A7E]" />
              </div>
              <div>
                <h4 className="text-white font-semibold">Become a Host</h4>
                <p className="text-sm text-gray-400">Share your adventure expertise and earn with us</p>
              </div>
            </div>
            <Link to="/become-host" data-testid="become-host-btn">
              <button className="px-6 py-2.5 bg-[#EB5A7E] hover:bg-[#D64566] text-white rounded-full text-sm font-semibold transition-colors whitespace-nowrap">
                Apply Now
              </button>
            </Link>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-gray-800">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <p className="text-sm text-gray-400">&copy; {currentYear} Seeker Adventure. All rights reserved.</p>
            <div className="flex space-x-6">
              <Link to="/terms" className="text-sm hover:text-[#F5A623] transition-colors">Terms & Conditions</Link>
              <Link to="/terms" className="text-sm hover:text-[#F5A623] transition-colors">Privacy Policy</Link>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
