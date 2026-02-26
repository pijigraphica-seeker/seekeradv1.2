import React, { useState, useRef, useEffect } from 'react';
import { Search, X, Plus, Minus, ChevronDown } from 'lucide-react';
import { Button } from './ui/button';
import { useNavigate } from 'react-router-dom';

const AirbnbSearchBar = ({ onSearch, compact = false }) => {
  const navigate = useNavigate();
  const [activeField, setActiveField] = useState(null);
  const [showMobileSearch, setShowMobileSearch] = useState(false);
  const containerRef = useRef(null);
  
  const [searchData, setSearchData] = useState({
    destination: '',
    date: null,
    guests: 1
  });

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setActiveField(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = () => {
    const params = new URLSearchParams();
    if (searchData.destination) params.set('search', searchData.destination);
    navigate(`/adventures?${params.toString()}`);
    setActiveField(null);
    setShowMobileSearch(false);
  };

  // Sample destinations
  const destinations = [
    { name: 'Indonesia', subtitle: 'Popular destination' },
    { name: 'Central Java', subtitle: 'Mountains & Volcanoes' },
    { name: 'Lombok', subtitle: 'Mount Rinjani' },
    { name: 'Bali', subtitle: 'Beaches & Waterfalls' },
    { name: 'Komodo', subtitle: 'Diving & Dragons' },
  ];

  // Sample dates
  const upcomingDates = [
    'Any time',
    'This weekend',
    'Next week',
    'April 2025',
    'May 2025',
    'June 2025',
  ];

  // Mobile Search Modal
  if (showMobileSearch) {
    return (
      <div className="fixed inset-0 bg-white z-50 overflow-y-auto md:hidden">
        <div className="p-4">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <button 
              onClick={() => setShowMobileSearch(false)}
              className="w-10 h-10 rounded-full border flex items-center justify-center"
            >
              <X className="w-5 h-5" />
            </button>
            <span className="font-semibold">Search adventures</span>
            <div className="w-10"></div>
          </div>

          {/* Where */}
          <div className="mb-4">
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Where</label>
            <input
              type="text"
              placeholder="Search destinations"
              value={searchData.destination}
              onChange={(e) => setSearchData({ ...searchData, destination: e.target.value })}
              className="w-full mt-2 p-4 text-lg border-2 rounded-xl focus:border-[#EB5A7E] outline-none"
            />
            <div className="flex flex-wrap gap-2 mt-3">
              {destinations.map((dest) => (
                <button
                  key={dest.name}
                  onClick={() => setSearchData({ ...searchData, destination: dest.name })}
                  className="px-4 py-2 rounded-full border hover:border-[#EB5A7E] text-sm"
                >
                  {dest.name}
                </button>
              ))}
            </div>
          </div>

          {/* When */}
          <div className="mb-4">
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">When</label>
            <div className="flex flex-wrap gap-2 mt-2">
              {upcomingDates.map((date) => (
                <button
                  key={date}
                  onClick={() => setSearchData({ ...searchData, date })}
                  className={`px-4 py-2 rounded-full border text-sm transition-colors ${
                    searchData.date === date 
                      ? 'border-[#EB5A7E] bg-[#EB5A7E]/10 text-[#EB5A7E]' 
                      : 'hover:border-gray-400'
                  }`}
                >
                  {date}
                </button>
              ))}
            </div>
          </div>

          {/* Who */}
          <div className="mb-6">
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Who</label>
            <div className="flex items-center justify-between mt-2 p-4 border-2 rounded-xl">
              <div>
                <div className="font-medium">Guests</div>
                <div className="text-sm text-gray-500">Add guests</div>
              </div>
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setSearchData({ ...searchData, guests: Math.max(1, searchData.guests - 1) })}
                  disabled={searchData.guests <= 1}
                  className="w-10 h-10 rounded-full border-2 border-gray-300 flex items-center justify-center hover:border-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Minus className="w-4 h-4" />
                </button>
                <span className="w-8 text-center font-semibold text-lg">{searchData.guests}</span>
                <button
                  onClick={() => setSearchData({ ...searchData, guests: searchData.guests + 1 })}
                  className="w-10 h-10 rounded-full border-2 border-gray-300 flex items-center justify-center hover:border-gray-900"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Search Button */}
          <Button
            onClick={handleSearch}
            className="w-full h-14 bg-gradient-to-r from-[#EB5A7E] to-[#F5A623] hover:from-[#D64566] hover:to-[#E09316] text-white text-lg font-semibold rounded-xl"
          >
            <Search className="w-5 h-5 mr-2" />
            Search
          </Button>
        </div>
      </div>
    );
  }

  // Compact Mobile Search Button
  if (compact) {
    return (
      <>
        {/* Mobile */}
        <button
          onClick={() => setShowMobileSearch(true)}
          className="md:hidden flex items-center gap-3 w-full px-4 py-3 bg-white rounded-full shadow-lg border border-gray-200"
        >
          <Search className="w-5 h-5 text-[#EB5A7E]" />
          <div className="flex-1 text-left">
            <div className="text-sm font-semibold text-gray-900">Where to?</div>
            <div className="text-xs text-gray-500">Anywhere • Any time • Add guests</div>
          </div>
        </button>
        
        {/* Desktop */}
        <button
          onClick={() => setActiveField('destination')}
          className="hidden md:flex items-center gap-3 px-5 py-3 bg-white rounded-full shadow-md hover:shadow-xl transition-shadow border border-gray-200 max-w-md mx-auto"
        >
          <Search className="w-5 h-5 text-gray-700" />
          <div className="flex-1 text-left">
            <span className="text-sm font-semibold text-gray-900">Start your search</span>
          </div>
          <div className="w-8 h-8 bg-gradient-to-r from-[#EB5A7E] to-[#F5A623] rounded-full flex items-center justify-center">
            <Search className="w-4 h-4 text-white" />
          </div>
        </button>
      </>
    );
  }

  return (
    <div ref={containerRef} className="w-full relative">
      {/* Mobile Search Button */}
      <button
        onClick={() => setShowMobileSearch(true)}
        className="md:hidden flex items-center gap-3 w-full max-w-md mx-auto px-4 py-3 bg-white rounded-full shadow-lg border border-gray-200"
      >
        <Search className="w-5 h-5 text-[#EB5A7E]" />
        <div className="flex-1 text-left">
          <div className="text-sm font-semibold text-gray-900">Where to?</div>
          <div className="text-xs text-gray-500">Anywhere • Any time • Add guests</div>
        </div>
      </button>

      {/* Desktop Search Bar */}
      <div className="hidden md:block bg-white rounded-full shadow-lg border border-gray-200 max-w-3xl mx-auto">
        <div className="flex items-center">
          {/* Where */}
          <div className="relative flex-1">
            <button
              onClick={() => setActiveField(activeField === 'where' ? null : 'where')}
              className={`w-full px-6 py-4 text-left rounded-full transition-all ${
                activeField === 'where' ? 'bg-gray-100 shadow-inner' : 'hover:bg-gray-50'
              }`}
            >
              <div className="text-xs font-bold text-gray-800">Where</div>
              <div className="text-sm text-gray-500 truncate">
                {searchData.destination || 'Search destinations'}
              </div>
            </button>
            
            {/* Where Dropdown */}
            {activeField === 'where' && (
              <div className="absolute top-full left-0 mt-3 w-96 bg-white rounded-3xl shadow-2xl border p-4 z-50">
                <input
                  type="text"
                  placeholder="Search destinations"
                  value={searchData.destination}
                  onChange={(e) => setSearchData({ ...searchData, destination: e.target.value })}
                  className="w-full p-3 border rounded-xl mb-4 focus:outline-none focus:border-[#EB5A7E]"
                  autoFocus
                />
                <div className="space-y-1">
                  {destinations.map((dest) => (
                    <button
                      key={dest.name}
                      onClick={() => {
                        setSearchData({ ...searchData, destination: dest.name });
                        setActiveField('when');
                      }}
                      className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 transition-colors text-left"
                    >
                      <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center">
                        <Search className="w-5 h-5 text-gray-400" />
                      </div>
                      <div>
                        <div className="font-medium text-gray-900">{dest.name}</div>
                        <div className="text-sm text-gray-500">{dest.subtitle}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="w-px h-8 bg-gray-200"></div>

          {/* When */}
          <div className="relative flex-1">
            <button
              onClick={() => setActiveField(activeField === 'when' ? null : 'when')}
              className={`w-full px-6 py-4 text-left rounded-full transition-all ${
                activeField === 'when' ? 'bg-gray-100 shadow-inner' : 'hover:bg-gray-50'
              }`}
            >
              <div className="text-xs font-bold text-gray-800">When</div>
              <div className="text-sm text-gray-500">
                {searchData.date || 'Add dates'}
              </div>
            </button>
            
            {/* When Dropdown */}
            {activeField === 'when' && (
              <div className="absolute top-full left-1/2 -translate-x-1/2 mt-3 w-80 bg-white rounded-3xl shadow-2xl border p-4 z-50">
                <div className="text-sm font-semibold text-gray-700 mb-3">When do you want to go?</div>
                <div className="grid grid-cols-2 gap-2">
                  {upcomingDates.map((date) => (
                    <button
                      key={date}
                      onClick={() => {
                        setSearchData({ ...searchData, date });
                        setActiveField('who');
                      }}
                      className={`p-3 rounded-xl text-sm font-medium transition-colors ${
                        searchData.date === date
                          ? 'bg-[#EB5A7E] text-white'
                          : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                      }`}
                    >
                      {date}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="w-px h-8 bg-gray-200"></div>

          {/* Who */}
          <div className="relative flex-1">
            <button
              onClick={() => setActiveField(activeField === 'who' ? null : 'who')}
              className={`w-full px-6 py-4 text-left rounded-full transition-all ${
                activeField === 'who' ? 'bg-gray-100 shadow-inner' : 'hover:bg-gray-50'
              }`}
            >
              <div className="text-xs font-bold text-gray-800">Who</div>
              <div className="text-sm text-gray-500">
                {searchData.guests > 1 ? `${searchData.guests} guests` : 'Add guests'}
              </div>
            </button>
            
            {/* Who Dropdown */}
            {activeField === 'who' && (
              <div className="absolute top-full right-0 mt-3 w-72 bg-white rounded-3xl shadow-2xl border p-6 z-50">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-gray-900">Guests</div>
                    <div className="text-sm text-gray-500">How many people?</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setSearchData({ ...searchData, guests: Math.max(1, searchData.guests - 1) })}
                      disabled={searchData.guests <= 1}
                      className="w-9 h-9 rounded-full border-2 border-gray-300 flex items-center justify-center hover:border-gray-900 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      <Minus className="w-4 h-4" />
                    </button>
                    <span className="w-6 text-center font-semibold">{searchData.guests}</span>
                    <button
                      onClick={() => setSearchData({ ...searchData, guests: searchData.guests + 1 })}
                      className="w-9 h-9 rounded-full border-2 border-gray-300 flex items-center justify-center hover:border-gray-900 transition-colors"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Search Button */}
          <div className="pr-2">
            <Button
              onClick={handleSearch}
              className="w-12 h-12 rounded-full bg-gradient-to-r from-[#EB5A7E] to-[#F5A623] hover:from-[#D64566] hover:to-[#E09316] text-white shadow-md hover:shadow-lg transition-all"
            >
              <Search className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AirbnbSearchBar;
