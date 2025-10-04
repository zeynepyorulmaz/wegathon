'use client';

import { Plane, Briefcase, ArrowRight } from 'lucide-react';

interface FlightSegment {
  fromIata: string;
  toIata: string;
  departISO: string;
  arriveISO: string;
  airline: string;
  flightNumber: string;
  durationMinutes: number;
}

interface FlightOption {
  provider: string;
  price?: number;
  currency?: string;
  segments: FlightSegment[];
  baggage?: string;
  refundable?: boolean;
  bookingUrl?: string;
}

interface FlightCardProps {
  flight: FlightOption;
  type: 'outbound' | 'inbound';
}

export function FlightCard({ flight, type }: FlightCardProps) {
  if (!flight || !flight.segments || flight.segments.length === 0) {
    return null;
  }

  const mainSegment = flight.segments[0];
  
  // Parse ISO dates safely
  const parseDepartDate = (iso: string) => {
    try {
      // If empty string or invalid, return null instead of today's date
      if (!iso || iso.trim() === '') {
        return null;
      }
      const date = new Date(iso);
      return isNaN(date.getTime()) ? null : date;
    } catch {
      return null;
    }
  };
  
  const departDate = parseDepartDate(mainSegment.departISO);
  const arriveDate = parseDepartDate(mainSegment.arriveISO);
  
  const departTime = departDate?.toLocaleTimeString('tr-TR', { 
    hour: '2-digit', 
    minute: '2-digit' 
  }) || '--:--';
  
  const arriveTime = arriveDate?.toLocaleTimeString('tr-TR', { 
    hour: '2-digit', 
    minute: '2-digit' 
  }) || '--:--';
  
  const departDateStr = departDate?.toLocaleDateString('tr-TR', { 
    day: '2-digit', 
    month: 'short',
    year: 'numeric'
  }) || 'Tarih belirtilmemiş';
  
  const departDateShort = departDate?.toLocaleDateString('tr-TR', { 
    day: '2-digit', 
    month: 'short'
  }) || 'Tarih belirtilmemiş';
  
  const departDayName = departDate?.toLocaleDateString('tr-TR', { 
    weekday: 'short'
  }) || '--';
  
  const arriveDateStr = arriveDate?.toLocaleDateString('tr-TR', { 
    day: '2-digit', 
    month: 'short'
  }) || 'Tarih belirtilmemiş';

  const hours = Math.floor(mainSegment.durationMinutes / 60);
  const minutes = mainSegment.durationMinutes % 60;
  const durationDisplay = mainSegment.durationMinutes > 0 
    ? `${hours}s ${minutes}dk` 
    : '--';
  
  // No dummy booking code; only show data we actually have

  return (
    <div className="relative w-full mx-auto">
      {/* Boarding Pass Container */}
      <div className="relative bg-gradient-to-br from-gray-50 to-white dark:from-gray-900 dark:to-gray-800 rounded-2xl shadow-md overflow-hidden border border-gray-200 dark:border-gray-700">
        
        {/* Airline branding bar */}
        <div className={`relative h-14 ${type === 'outbound' ? 'bg-gradient-to-r from-blue-600 via-blue-500 to-sky-500' : 'bg-gradient-to-r from-indigo-600 via-purple-500 to-pink-500'} overflow-hidden`}>
          {/* Subtle pattern overlay */}
          <div className="absolute inset-0 opacity-10" style={{
            backgroundImage: 'radial-gradient(circle at 2px 2px, white 1px, transparent 0)',
            backgroundSize: '24px 24px'
          }} />
          
          <div className="relative h-full px-5 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-white dark:bg-gray-900 rounded-lg flex items-center justify-center shadow">
                <Plane className={`h-6 w-6 ${type === 'outbound' ? 'text-blue-600 rotate-45' : 'text-purple-600 -rotate-45'}`} />
              </div>
              <div className="text-white">
                <div className="text-lg font-black tracking-tight truncate max-w-[200px]">{mainSegment.airline}</div>
                <div className="text-[10px] font-bold opacity-90 uppercase tracking-widest">{type === 'outbound' ? 'Gidiş Uçuşu' : 'Dönüş Uçuşu'}</div>
              </div>
            </div>
            
            {flight.price && (
              <div className="bg-white/20 backdrop-blur-sm border border-white/30 rounded-xl px-4 py-2 text-right">
                <div className="text-xl sm:text-2xl font-black text-white leading-none tracking-tight">
                  ₺{flight.price.toLocaleString('tr-TR')}
                </div>
                <div className="text-[10px] text-white/90 font-semibold mt-0.5">
                  Kişi Başı
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* Main Ticket Body */}
        <div className="relative bg-white dark:bg-gray-900">
          
          {/* Slim meta bar (no dummy values) */}
          <div className="px-8 py-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-6 text-xs text-gray-600 dark:text-gray-400">
              <div className="font-semibold uppercase tracking-wider">Uçuş No:</div>
              <div className="font-bold text-gray-900 dark:text-white">{mainSegment.flightNumber}</div>
              <div className="h-4 w-px bg-gray-300 dark:bg-gray-600" />
              <div className="font-semibold uppercase tracking-wider">Tarih:</div>
              <div className="font-bold text-gray-900 dark:text-white">{departDayName}, {departDateShort}</div>
            </div>
          </div>
          
          {/* Flight Route Section - Large Format */}
          <div className="px-5 py-6">
            <div className="grid grid-cols-[1fr,auto,1fr] gap-6 items-center">
              
              {/* Departure */}
              <div className="space-y-4">
                  <div className="text-[10px] font-black text-gray-400 dark:text-gray-500 uppercase tracking-[0.2em] mb-1.5">
                    Kalkış
                  </div>
                  <div className="space-y-2">
                    <div className="text-3xl sm:text-4xl md:text-5xl font-black text-gray-900 dark:text-white font-mono tracking-tight leading-none">
                      {departTime}
                    </div>
                    <div className="flex items-baseline gap-3">
                      <div className="text-2xl sm:text-3xl md:text-4xl font-black text-gray-900 dark:text-white tracking-tight">
                        {mainSegment.fromIata}
                      </div>
                    </div>
                    <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 font-semibold">
                      {departDateStr}
                    </div>
                </div>
              </div>

              {/* Flight Path - Enhanced */}
              <div className="flex flex-col items-center px-6">
                  <div className="relative mb-3">
                    {/* Animated flight path */}
                    <div className="relative w-24 sm:w-28 md:w-32 h-2">
                      <div className="absolute inset-0 flex items-center">
                        <div className="w-full h-0.5 bg-gradient-to-r from-blue-500 via-sky-400 to-blue-500"></div>
                      </div>
                      {/* Departure dot */}
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full bg-blue-600 ring-4 ring-blue-200 dark:ring-blue-900"></div>
                      {/* Arrival dot */}
                      <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full bg-blue-600 ring-4 ring-blue-200 dark:ring-blue-900"></div>
                      {/* Plane */}
                      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
                        <div className={`p-1.5 ${type === 'outbound' ? 'bg-blue-500' : 'bg-purple-500'} rounded-full`}>
                          <Plane className="h-4 w-4 text-white rotate-90" />
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Flight info */}
                  <div className="text-center space-y-2">
                    <div>
                      <div className="text-[10px] font-black text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-1">
                        Uçuş Süresi
                      </div>
                      <div className="text-sm sm:text-base font-black text-gray-900 dark:text-white">
                        {durationDisplay}
                      </div>
                    </div>
                    {flight.segments.length > 1 ? (
                      <div className="px-3 py-1.5 bg-orange-500 text-white rounded-lg text-[10px] font-black uppercase tracking-wide">
                        {flight.segments.length - 1} Aktarma
                      </div>
                    ) : (
                      <div className="px-3 py-1.5 bg-green-500 text-white rounded-lg text-[10px] font-black uppercase tracking-wide flex items-center gap-2">
                        <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                        Direkt Uçuş
                      </div>
                  )}
                </div>
              </div>

              {/* Arrival */}
              <div className="text-right space-y-4">
                  <div className="text-[10px] font-black text-gray-400 dark:text-gray-500 uppercase tracking-[0.2em] mb-1.5">
                    Varış
                  </div>
                  <div className="space-y-2">
                    <div className="text-3xl sm:text-4xl md:text-5xl font-black text-gray-900 dark:text-white font-mono tracking-tight leading-none">
                      {arriveTime}
                    </div>
                    <div className="flex items-baseline gap-3 justify-end">
                      <div className="text-2xl sm:text-3xl md:text-4xl font-black text-gray-900 dark:text-white tracking-tight">
                        {mainSegment.toIata}
                      </div>
                    </div>
                    <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 font-semibold">
                      {arriveDateStr}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Passenger info removed (no dummy values) */}

          {/* Bottom Section */}
          <div className="px-5 py-5">
            <div className="grid grid-cols-2 gap-6 mb-6">
              {/* Baggage Allowance (only if provided) */}
              {flight.baggage && (
                <div className="bg-gray-50 dark:bg-gray-800 rounded-2xl p-4 border-2 border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-3">
                    <div className={`p-3 rounded-xl ${type === 'outbound' ? 'bg-blue-100 dark:bg-blue-900' : 'bg-purple-100 dark:bg-purple-900'}`}>
                      <Briefcase className={`h-6 w-6 ${type === 'outbound' ? 'text-blue-600 dark:text-blue-400' : 'text-purple-600 dark:text-purple-400'}`} />
                    </div>
                    <div>
                      <div className="text-[9px] font-black text-gray-500 dark:text-gray-400 uppercase tracking-widest mb-1">
                        Bagaj
                      </div>
                      <div className="text-lg font-black text-gray-900 dark:text-white">
                        {flight.baggage}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Provider removed (not critical to ticket UI) */}
            </div>

            {/* Status badges removed (keep UI minimal and data-driven) */}

            {/* Booking CTA */}
            {flight.bookingUrl && (
                <a
                  href={flight.bookingUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`block w-full text-center ${type === 'outbound' ? 'bg-gradient-to-r from-blue-600 to-sky-500 hover:from-blue-700 hover:to-sky-600' : 'bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600'} text-white py-3.5 px-5 rounded-xl font-bold text-sm uppercase tracking-wider transition-colors shadow hover:shadow-md`}
                >
                  <div className="flex items-center justify-center gap-3">
                    <span>Rezervasyon Yap</span>
                    <ArrowRight className="h-6 w-6" />
                </div>
              </a>
            )}
          </div>

          {/* Footer divider */}
          <div className="px-5 py-3">
            <div className="border-t-2 border-dashed border-gray-200 dark:border-gray-700" />
          </div>
        </div>
      </div>
    </div>
  );
}
