"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Share2, Copy, Check, Link2, Clock, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { createShareLink, type CreateShareRequest, type CreateShareResponse } from "@/services/sharing-api";

interface ShareTripModalProps {
  isOpen: boolean;
  onClose: () => void;
  tripId: string;
  tripTitle: string;
  ownerName?: string;
  tripData?: Record<string, unknown>;  // Trip data to cache on backend
}

export function ShareTripModal({
  isOpen,
  onClose,
  tripId,
  tripTitle,
  ownerName = "Anonymous",
  tripData,
}: ShareTripModalProps) {
  const [permissionLevel, setPermissionLevel] = useState<"view" | "suggest" | "edit">("suggest");
  const [isPublic, setIsPublic] = useState(true);
  const [expiresInDays, setExpiresInDays] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [shareData, setShareData] = useState<CreateShareResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCreateShare = async () => {
    setLoading(true);
    try {
      const request: CreateShareRequest = {
        trip_id: tripId,
        permission_level: permissionLevel,
        is_public: isPublic,
        expires_in_days: expiresInDays || undefined,
        owner_name: ownerName,
        trip_data: tripData,  // Send trip data to cache
      };

      const response = await createShareLink(request);
      setShareData(response);
    } catch (error) {
      console.error("Failed to create share link:", error);
      alert("Failed to create share link. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = () => {
    if (!shareData) return;
    
    const fullUrl = `${window.location.origin}${shareData.share_url}`;
    navigator.clipboard.writeText(fullUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    setShareData(null);
    setCopied(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
        onClick={handleClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="relative w-full max-w-lg"
          onClick={(e) => e.stopPropagation()}
        >
          <Card className="border-2">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Share2 className="h-5 w-5 text-primary" />
                  <CardTitle>Gezi Planını Paylaş</CardTitle>
                </div>
                <Button variant="ghost" size="icon" onClick={handleClose}>
                  <X className="h-5 w-5" />
                </Button>
              </div>
              <CardDescription>{tripTitle}</CardDescription>
            </CardHeader>

            <CardContent className="space-y-6">
              {!shareData ? (
                <>
                  {/* Permission Level */}
                  <div className="space-y-3">
                    <label className="text-sm font-medium">İzin Seviyesi</label>
                    <div className="grid grid-cols-3 gap-2">
                      <Button
                        variant={permissionLevel === "view" ? "default" : "outline"}
                        size="sm"
                        onClick={() => setPermissionLevel("view")}
                        className="flex flex-col h-auto py-3"
                      >
                        <span className="text-xs">Görüntüle</span>
                        <span className="text-[10px] opacity-70 mt-1">Sadece bakabilir</span>
                      </Button>
                      <Button
                        variant={permissionLevel === "suggest" ? "default" : "outline"}
                        size="sm"
                        onClick={() => setPermissionLevel("suggest")}
                        className="flex flex-col h-auto py-3"
                      >
                        <span className="text-xs">Öneri</span>
                        <span className="text-[10px] opacity-70 mt-1">Alternatif önerebilir</span>
                      </Button>
                      <Button
                        variant={permissionLevel === "edit" ? "default" : "outline"}
                        size="sm"
                        onClick={() => setPermissionLevel("edit")}
                        className="flex flex-col h-auto py-3"
                      >
                        <span className="text-xs">Düzenle</span>
                        <span className="text-[10px] opacity-70 mt-1">Direkt değiştirebilir</span>
                      </Button>
                    </div>
                  </div>

                  {/* Public/Private */}
                  <div className="space-y-3">
                    <label className="text-sm font-medium">Erişim</label>
                    <div className="grid grid-cols-2 gap-2">
                      <Button
                        variant={isPublic ? "default" : "outline"}
                        size="sm"
                        onClick={() => setIsPublic(true)}
                        className="flex items-center gap-2"
                      >
                        <Users className="h-4 w-4" />
                        <span>Herkese Açık</span>
                      </Button>
                      <Button
                        variant={!isPublic ? "default" : "outline"}
                        size="sm"
                        onClick={() => setIsPublic(false)}
                        className="flex items-center gap-2"
                      >
                        <Link2 className="h-4 w-4" />
                        <span>Linkle Erişim</span>
                      </Button>
                    </div>
                  </div>

                  {/* Expiration */}
                  <div className="space-y-3">
                    <label className="text-sm font-medium flex items-center gap-2">
                      <Clock className="h-4 w-4" />
                      Süre Sınırı (Opsiyonel)
                    </label>
                    <div className="grid grid-cols-4 gap-2">
                      {[7, 30, 90, null].map((days) => (
                        <Button
                          key={days || "never"}
                          variant={expiresInDays === days ? "default" : "outline"}
                          size="sm"
                          onClick={() => setExpiresInDays(days)}
                        >
                          {days ? `${days} gün` : "Sınırsız"}
                        </Button>
                      ))}
                    </div>
                  </div>

                  {/* Create Button */}
                  <Button
                    className="w-full"
                    onClick={handleCreateShare}
                    disabled={loading}
                  >
                    {loading ? "Oluşturuluyor..." : "Paylaşım Linki Oluştur"}
                  </Button>
                </>
              ) : (
                <>
                  {/* Success State */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-center py-4">
                      <div className="relative">
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ type: "spring", duration: 0.5 }}
                          className="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center"
                        >
                          <Check className="h-8 w-8 text-green-600 dark:text-green-400" />
                        </motion.div>
                      </div>
                    </div>

                    <div className="text-center space-y-2">
                      <h3 className="font-semibold text-lg">Paylaşım Linki Hazır! 🎉</h3>
                      <p className="text-sm text-muted-foreground">
                        Bu linki arkadaşlarınla paylaşabilirsin
                      </p>
                    </div>

                    {/* Link Display */}
                    <div className="relative">
                      <div className="flex items-center gap-2 p-3 bg-muted rounded-lg border">
                        <Link2 className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        <code className="text-xs flex-1 overflow-hidden text-ellipsis whitespace-nowrap">
                          {window.location.origin}{shareData.share_url}
                        </code>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="absolute right-2 top-1/2 -translate-y-1/2"
                        onClick={handleCopyLink}
                      >
                        {copied ? (
                          <>
                            <Check className="h-4 w-4 mr-1" />
                            Kopyalandı
                          </>
                        ) : (
                          <>
                            <Copy className="h-4 w-4 mr-1" />
                            Kopyala
                          </>
                        )}
                      </Button>
                    </div>

                    {/* Share Details */}
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="secondary">
                        {permissionLevel === "view" ? "Görüntüleme" : permissionLevel === "suggest" ? "Öneri" : "Düzenleme"}
                      </Badge>
                      <Badge variant="secondary">
                        {isPublic ? "Herkese Açık" : "Linkle Erişim"}
                      </Badge>
                      {expiresInDays && (
                        <Badge variant="secondary">
                          {expiresInDays} gün geçerli
                        </Badge>
                      )}
                    </div>

                    {/* Close Button */}
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={handleClose}
                    >
                      Kapat
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
