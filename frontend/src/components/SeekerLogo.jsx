import React from 'react';

const SeekerLogo = ({ className = "w-10 h-10", showText = false, textSize = "text-xl" }) => {
  return (
    <div className="flex items-center space-x-2">
      {/* Logo Icon - Mountain with location pin */}
      <div className={`${className} relative flex items-center justify-center`}>
        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Mountain shapes in red/coral */}
          <path
            d="M20 80 L40 40 L60 80 Z"
            fill="#E74C3C"
            opacity="0.8"
          />
          <path
            d="M40 80 L60 50 L80 80 Z"
            fill="#FF6B6B"
          />
          {/* Location pin in teal */}
          <g>
            {/* Pin circle */}
            <circle cx="70" cy="35" r="12" fill="#00CED1" />
            {/* Pin point */}
            <path
              d="M70 47 C70 47, 75 52, 70 58 C65 52, 70 47, 70 47 Z"
              fill="#00CED1"
            />
            {/* Inner dot */}
            <circle cx="70" cy="35" r="5" fill="white" />
          </g>
        </svg>
      </div>
      
      {/* Text logo */}
      {showText && (
        <div className="flex flex-col leading-tight">
          <span className={`${textSize} font-bold text-[#E74C3C] tracking-wide`}>
            Seeker
          </span>
          <span className="text-xs italic text-gray-700 -mt-1">
            adventure
          </span>
        </div>
      )}
    </div>
  );
};

export default SeekerLogo;
