"use client";

import React from "react";
import { Sparkles } from "lucide-react";

export interface CheckoutBannersProps {
  checkoutResult: string | null;
  checkoutError: string | null;
}

export function CheckoutBanners({ checkoutResult, checkoutError }: CheckoutBannersProps) {
  return (
    <>
      {checkoutResult === "success" && (
        <div className="flex items-center gap-2 rounded-lg border border-green-500/30 bg-green-500/10 px-4 py-3">
          <Sparkles className="h-5 w-5 text-green-600 flex-shrink-0" />
          <p className="text-sm font-medium text-green-700">
            Subscription activated! Your plan has been upgraded.
          </p>
        </div>
      )}
      {checkoutResult === "cancelled" && (
        <div className="flex items-center gap-2 rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-3">
          <p className="text-sm text-yellow-700">
            Checkout was cancelled. You can try again anytime.
          </p>
        </div>
      )}
      {checkoutError && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3">
          <p className="text-sm text-destructive">
            {checkoutError === "stripe_not_configured"
              ? "Payment processing is not yet configured. Please contact support."
              : checkoutError === "price_not_configured"
                ? "This plan is not available for purchase yet."
                : "An error occurred. Please try again."}
          </p>
        </div>
      )}
    </>
  );
}
