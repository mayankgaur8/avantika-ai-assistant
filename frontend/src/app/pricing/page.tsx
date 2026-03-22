"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { billingApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Check } from "lucide-react";
import Link from "next/link";

declare const Razorpay: any;

export default function PricingPage() {
  const { isAuthenticated } = useAuthStore();

  const { data: plansData } = useQuery({
    queryKey: ["plans"],
    queryFn: () => billingApi.plans().then((r) => r.data),
  });

  const checkoutMutation = useMutation({
    mutationFn: ({ plan_name, billing_period }: { plan_name: string; billing_period: "monthly" | "yearly" }) =>
      billingApi.checkout(plan_name, billing_period).then((r) => r.data),
    onSuccess: (data) => {
      const rzp = new Razorpay({
        key: process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID,
        subscription_id: data.checkout.razorpay_subscription_id,
        name: "Avantika Global Language AI",
        description: `${data.checkout.plan_name} Plan — ${data.checkout.billing_period}`,
        handler: () => {
          toast.success("Subscription activated! Redirecting...");
          setTimeout(() => window.location.href = "/dashboard", 2000);
        },
      });
      rzp.open();
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "Checkout failed"),
  });

  const plans = plansData?.plans || [];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Simple, Honest Pricing</h1>
          <p className="text-gray-500 text-lg">India-friendly pricing. Cancel anytime.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {plans.filter((p: any) => p.name !== "enterprise").map((plan: any) => (
            <div
              key={plan.name}
              className={`card relative ${plan.name === "premium" ? "ring-2 ring-brand-500 shadow-lg" : ""}`}
            >
              {plan.name === "premium" && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="badge-blue px-4 py-1 text-xs font-semibold rounded-full">Most Popular</span>
                </div>
              )}
              <div className="mb-6">
                <h2 className="text-xl font-bold text-gray-900">{plan.display_name}</h2>
                <div className="mt-3">
                  {plan.monthly_price_inr === 0 ? (
                    <span className="text-4xl font-extrabold text-gray-900">Free</span>
                  ) : (
                    <>
                      <span className="text-4xl font-extrabold text-gray-900">₹{plan.monthly_price_inr}</span>
                      <span className="text-gray-500 text-sm">/month</span>
                    </>
                  )}
                  {plan.yearly_price_inr > 0 && (
                    <p className="text-sm text-green-600 mt-1">₹{plan.yearly_price_inr}/year (save ~25%)</p>
                  )}
                </div>
                <p className="text-sm text-gray-500 mt-2">{plan.monthly_requests} requests/month</p>
              </div>

              <ul className="space-y-2.5 mb-8">
                {plan.features?.map((f: string, i: number) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-gray-700">
                    <Check className="h-4 w-4 text-green-500 flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>

              {plan.name === "free" ? (
                isAuthenticated ? (
                  <Link href="/dashboard" className="btn-secondary w-full text-center block">
                    Go to Dashboard
                  </Link>
                ) : (
                  <Link href="/register" className="btn-secondary w-full text-center block">
                    Get Started Free
                  </Link>
                )
              ) : (
                isAuthenticated ? (
                  <button
                    onClick={() => checkoutMutation.mutate({ plan_name: plan.name, billing_period: "monthly" })}
                    disabled={checkoutMutation.isPending}
                    className="btn-primary w-full"
                  >
                    {checkoutMutation.isPending ? "Loading..." : `Subscribe to ${plan.display_name}`}
                  </button>
                ) : (
                  <Link href="/register" className="btn-primary w-full text-center block">
                    Get Started
                  </Link>
                )
              )}
            </div>
          ))}
        </div>

        {/* Enterprise */}
        <div className="card mt-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <h3 className="font-bold text-gray-900 text-lg">Enterprise</h3>
            <p className="text-gray-500 text-sm mt-1">Team dashboards, custom integrations, SLA, dedicated support. Custom pricing.</p>
          </div>
          <a href="mailto:sales@avantika.ai" className="btn-secondary whitespace-nowrap">Contact Sales</a>
        </div>
      </div>
    </div>
  );
}
