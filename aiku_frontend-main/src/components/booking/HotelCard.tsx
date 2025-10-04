'use client';

import { Hotel, MapPin, Star, Calendar, Users, Wifi, Coffee, Car, CheckCircle, ArrowRight, Moon, Sun } from 'lucide-react';

interface HotelOption {
  provider: string;
  name: string;
  address?: string;
  checkInISO: string;
  checkOutISO: string;
  priceTotal?: number;
  currency?: string;
  rating?: number;
  amenities?: string[];
  neighborhood?: string;
  bookingUrl?: string;
}

interface HotelCardProps {
  hotel: HotelOption;
}

const amenityIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  wifi: Wifi,
  breakfast: Coffee,
  parking: Car,
};

export function HotelCard({ hotel }: HotelCardProps) {
  console.log('🏨 HotelCard received:', {
    hotel: hotel,
    name: hotel?.name,
    checkIn: hotel?.checkInISO,
    checkOut: hotel?.checkOutISO
  });

  if (!hotel) {
    return null;
  }

  const parseDate = (iso: string) => {
    try {
      const date = new Date(iso);
      return isNaN(date.getTime()) ? null : date;
    } catch {
      return null;
    }
  };

  const checkInDateObj = parseDate(hotel.checkInISO);
  const checkOutDateObj = parseDate(hotel.checkOutISO);

  const formatFullDate = (date: Date | null) => {
    if (!date) return '--';
    return date.toLocaleDateString('tr-TR', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  const formatShortDate = (date: Date | null) => {
    if (!date) return '--';
    return date.toLocaleDateString('tr-TR', {
      day: '2-digit',
      month: 'short'
    });
  };

  const checkInFull = formatFullDate(checkInDateObj);
  const checkOutFull = formatFullDate(checkOutDateObj);
  const checkInShort = formatShortDate(checkInDateObj);
  const checkOutShort = formatShortDate(checkOutDateObj);

  const nights = checkInDateObj && checkOutDateObj 
    ? Math.ceil((checkOutDateObj.getTime() - checkInDateObj.getTime()) / (1000 * 60 * 60 * 24))
    : null;

  const pricePerNight = hotel.priceTotal && nights ? Math.round(hotel.priceTotal / nights) : null;

  return (
    <div className="relative max-w-4xl mx-auto">
      {/* Hotel Voucher Container */}
      <div className="relative bg-white dark:bg-gray-900 rounded-3xl shadow-2xl overflow-hidden border-2 border-gray-200 dark:border-gray-700">
        
        {/* Decorative top banner with pattern */}
        <div className="relative h-3 bg-gradient-to-r from-amber-500 via-orange-400 to-pink-500">
          <div className="absolute inset-0 opacity-20" style={{
            backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 20px, white 20px, white 22px)',
          }} />
        </div>

        {/* Main Content */}
        <div className="p-8">
          
          {/* Header Section */}
          <div className="flex items-start justify-between mb-6 pb-6 border-b-2 border-dashed border-gray-200 dark:border-gray-700">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-3 bg-gradient-to-br from-amber-100 to-orange-100 dark:from-amber-900 dark:to-orange-900 rounded-xl">
                  <Hotel className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <div className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest mb-1">
                    Otel Rezervasyonu
                  </div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white leading-tight">
                    {hotel.name}
                  </h2>
                </div>
              </div>

              {/* Rating */}
              {hotel.rating && (
                <div className="flex items-center gap-2 mb-3">
                  <div className="flex items-center gap-0.5">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Star
                        key={i}
                        className={`h-4 w-4 ${
                          i < hotel.rating! 
                            ? 'fill-amber-400 text-amber-400' 
                            : 'fill-gray-200 text-gray-200 dark:fill-gray-700 dark:text-gray-700'
                        }`}
                      />
                    ))}
                  </div>
                  <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                    {hotel.rating} Yıldız
                  </span>
                </div>
              )}

              {/* Location */}
              {(hotel.neighborhood || hotel.address) && (
                <div className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <MapPin className="h-4 w-4 mt-0.5 flex-shrink-0 text-red-500" />
                  <span className="font-medium">{hotel.neighborhood || hotel.address}</span>
                </div>
              )}
            </div>

            {/* Price Badge */}
            {hotel.priceTotal && (
              <div className="ml-6 text-right bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-950 dark:to-orange-950 px-6 py-4 rounded-2xl border-2 border-amber-200 dark:border-amber-800">
                <div className="text-xs font-bold text-gray-600 dark:text-gray-400 uppercase tracking-wider mb-1">
                  Toplam Tutar
                </div>
                <div className="text-4xl font-bold text-amber-600 dark:text-amber-400 leading-none font-mono">
                  ₺{hotel.priceTotal.toLocaleString('tr-TR')}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  {hotel.currency || 'TRY'}
                  {nights && (
                    <span className="block mt-0.5 font-medium">
                      {nights} gece konaklama
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Check-in / Check-out Section - Voucher Style */}
          <div className="grid grid-cols-2 gap-6 mb-6">
            {/* Check-in */}
            <div className="bg-gradient-to-br from-blue-50 to-sky-50 dark:from-blue-950 dark:to-sky-950 rounded-2xl p-6 border border-blue-200 dark:border-blue-800">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                  <Sun className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="flex-1">
                  <div className="text-[10px] font-bold text-gray-600 dark:text-gray-400 uppercase tracking-widest mb-2">
                    Giriş Tarihi
                  </div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white font-mono mb-1">
                    {checkInShort}
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 font-medium">
                    {checkInFull}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-500 mt-2 font-semibold">
                    15:00'den sonra
                  </div>
                </div>
              </div>
            </div>

            {/* Check-out */}
            <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-950 dark:to-pink-950 rounded-2xl p-6 border border-purple-200 dark:border-purple-800">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
                  <Moon className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div className="flex-1">
                  <div className="text-[10px] font-bold text-gray-600 dark:text-gray-400 uppercase tracking-widest mb-2">
                    Çıkış Tarihi
                  </div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-white font-mono mb-1">
                    {checkOutShort}
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 font-medium">
                    {checkOutFull}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-500 mt-2 font-semibold">
                    11:00'e kadar
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Duration indicator */}
          {nights && (
            <div className="flex items-center justify-center gap-2 mb-6 py-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
              <Calendar className="h-4 w-4 text-gray-600 dark:text-gray-400" />
              <span className="text-sm font-bold text-gray-700 dark:text-gray-300">
                {nights} Gece Konaklama
              </span>
              {pricePerNight && (
                <>
                  <span className="text-gray-400 mx-2">•</span>
                  <span className="text-sm font-bold text-amber-600 dark:text-amber-400">
                    ₺{pricePerNight.toLocaleString('tr-TR')} / gece
                  </span>
                </>
              )}
            </div>
          )}

          {/* Amenities Section */}
          {hotel.amenities && hotel.amenities.length > 0 && (
            <div className="mb-6 pb-6 border-b-2 border-dashed border-gray-200 dark:border-gray-700">
              <div className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest mb-3">
                Otel Olanakları
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {hotel.amenities.map((amenity, i) => {
                  const Icon = amenityIcons[amenity.toLowerCase()] || CheckCircle;
                  return (
                    <div key={i} className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 px-3 py-2 rounded-lg">
                      <Icon className="h-4 w-4 text-green-600 dark:text-green-400" />
                      <span>{amenity}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Provider and Booking Info */}
          <div className="flex items-center justify-between">
            {/* Provider */}
            {hotel.provider && hotel.provider !== 'unknown' && hotel.provider !== 'mcp' && (
              <div className="flex items-center gap-2">
                <div className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest">
                  Sağlayıcı:
                </div>
                <div className="text-sm font-bold text-gray-900 dark:text-gray-100 capitalize px-3 py-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  {hotel.provider}
                </div>
              </div>
            )}

            {/* Booking Button */}
            {hotel.bookingUrl && (
              <a
                href={hotel.bookingUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 bg-gradient-to-r from-amber-600 to-orange-500 hover:from-amber-700 hover:to-orange-600 text-white px-6 py-3 rounded-xl font-bold text-sm uppercase tracking-wider transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
              >
                Rezervasyon Yap
                <ArrowRight className="h-5 w-5" />
              </a>
            )}
          </div>

          {/* Confirmation Badge */}
          <div className="mt-6 pt-6 border-t-2 border-dashed border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-center gap-2 text-green-600 dark:text-green-400">
              <CheckCircle className="h-5 w-5" />
              <span className="text-sm font-bold uppercase tracking-wide">
                Rezervasyon Onaylandı
              </span>
            </div>
          </div>
        </div>

        {/* Decorative bottom banner */}
        <div className="relative h-3 bg-gradient-to-r from-amber-500 via-orange-400 to-pink-500">
          <div className="absolute inset-0 opacity-20" style={{
            backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 20px, white 20px, white 22px)',
          }} />
        </div>
      </div>

      {/* Corner decorative elements - like voucher stamps */}
      <div className="absolute -top-2 -left-2 w-12 h-12 bg-gradient-to-br from-amber-400 to-orange-500 rounded-full opacity-20 blur-xl" />
      <div className="absolute -bottom-2 -right-2 w-16 h-16 bg-gradient-to-br from-pink-400 to-purple-500 rounded-full opacity-20 blur-xl" />
    </div>
  );
}
