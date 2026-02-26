import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Star, MapPin, Calendar, Users, Heart } from 'lucide-react';
import { getTripUrl } from '../services/api';
import { Button } from './ui/button';

const TripCard = ({ trip, compact = false }) => {
  const [isFavorite, setIsFavorite] = useState(false);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

  const handleFavoriteClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsFavorite(!isFavorite);
  };

  const handleNextImage = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setCurrentImageIndex((prev) => (prev + 1) % trip.images.length);
  };

  const handlePrevImage = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setCurrentImageIndex((prev) => (prev - 1 + trip.images.length) % trip.images.length);
  };

  return (
    <Link to={getTripUrl(trip)} data-testid={`trip-card-${trip.trip_id || trip.id}`}>
      <Card className="group overflow-hidden hover:shadow-xl transition-all duration-300 border-0 shadow-md">
        {/* Image Section */}
        <div className="relative aspect-[4/3] overflow-hidden bg-gray-200">
          <img
            src={trip.images[currentImageIndex]}
            alt={trip.title}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
          />
          
          {/* Image Navigation Dots */}
          {trip.images.length > 1 && (
            <>
              <div className="absolute bottom-3 left-1/2 transform -translate-x-1/2 flex space-x-1.5">
                {trip.images.map((_, index) => (
                  <div
                    key={index}
                    className={`w-1.5 h-1.5 rounded-full transition-all ${
                      index === currentImageIndex
                        ? 'bg-white w-5'
                        : 'bg-white/60'
                    }`}
                  />
                ))}
              </div>
              
              {/* Navigation Arrows - Show on hover */}
              <button
                onClick={handlePrevImage}
                className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-white/80 hover:bg-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <button
                onClick={handleNextImage}
                className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-white/80 hover:bg-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </>
          )}
          
          {/* Favorite Button */}
          <button
            onClick={handleFavoriteClick}
            className="absolute top-3 right-3 w-9 h-9 rounded-full bg-white/90 hover:bg-white flex items-center justify-center transition-all hover:scale-110"
          >
            <Heart
              className={`w-5 h-5 transition-colors ${
                isFavorite ? 'fill-red-500 text-red-500' : 'text-gray-700'
              }`}
            />
          </button>
          
          {/* Featured Badge */}
          {trip.featured && (
            <Badge className="absolute top-3 left-3 bg-emerald-500 hover:bg-emerald-600 text-white border-0">
              Featured
            </Badge>
          )}
        </div>

        <CardContent className="p-4">
          {/* Location & Rating */}
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center text-sm text-gray-600">
              <MapPin className="w-4 h-4 mr-1 flex-shrink-0" />
              <span className="line-clamp-1">{trip.location}</span>
            </div>
            <div className="flex items-center ml-2 flex-shrink-0">
              <Star className="w-4 h-4 text-yellow-400 fill-yellow-400 mr-1" />
              <span className="text-sm font-semibold">{trip.rating}</span>
              <span className="text-xs text-gray-500 ml-1">({trip.review_count || trip.reviewCount})</span>
            </div>
          </div>

          {/* Title */}
          <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2 group-hover:text-emerald-600 transition-colors">
            {trip.title}
          </h3>

          {/* Trip Details */}
          <div className="flex items-center space-x-3 text-sm text-gray-600 mb-3">
            <div className="flex items-center">
              <Calendar className="w-4 h-4 mr-1" />
              <span>{trip.duration}</span>
            </div>
            <div className="flex items-center">
              <Users className="w-4 h-4 mr-1" />
              <span>Max {trip.max_guests || trip.maxGuests}</span>
            </div>
          </div>

          {/* Difficulty Badge */}
          <Badge
            variant="outline"
            className={`mb-3 ${
              trip.difficulty === 'Easy'
                ? 'border-green-500 text-green-700 bg-green-50'
                : trip.difficulty === 'Moderate'
                ? 'border-yellow-500 text-yellow-700 bg-yellow-50'
                : 'border-red-500 text-red-700 bg-red-50'
            }`}
          >
            {trip.difficulty}
          </Badge>

          {/* Price */}
          <div className="flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-bold text-gray-900">
                {trip.currency}{trip.price}
              </span>
              <span className="text-sm text-gray-500 ml-1">/ person</span>
            </div>
            <div className="text-right">
              <div className="text-xs text-gray-500">Deposit from</div>
              <div className="text-sm font-semibold text-emerald-600">
                {trip.currency}{trip.deposit_price || trip.depositPrice}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
};

export default TripCard;
