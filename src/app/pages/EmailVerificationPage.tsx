import { useState, useRef, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { Mail, ArrowLeft, CheckCircle2, Loader2, ShieldCheck, MessageSquareCode } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { API_BASE_URL } from "../config/api";

export function EmailVerificationPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const emailParam = searchParams.get("email") || "";
  
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [message, setMessage] = useState("");
  
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const handleOtpChange = (index: number, value: string) => {
    if (value.length > 1) {
      // Handle paste
      const pastedData = value.slice(0, 6).split("");
      const newOtp = [...otp];
      pastedData.forEach((char, i) => {
        if (index + i < 6) newOtp[index + i] = char;
      });
      setOtp(newOtp);
      // Focus last filled or next empty
      const nextIndex = Math.min(index + pastedData.length, 5);
      inputRefs.current[nextIndex]?.focus();
      return;
    }

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // Move focus to next input if value is entered
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    const otpCode = otp.join("");
    if (otpCode.length < 6) {
      setError("Please enter the full 6-digit code.");
      return;
    }

    setIsLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/verify-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: emailParam, otp_code: otpCode }),
      });
      
      if (response.ok) {
        setSuccess(true);
        setTimeout(() => {
          navigate("/login");
        }, 3000);
      } else {
        const data = await response.json();
        setError(data.detail || "Invalid or expired verification code.");
      }
    } catch (err) {
      setError("Connection error. Please try again later.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    setIsResending(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/resend-verification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: emailParam }),
      });
      
      if (response.ok) {
        setMessage("Verification code resent successfully!");
      } else {
        const data = await response.json();
        setError(data.detail || "Failed to resend code.");
      }
    } catch (err) {
      setError("Connection error. Please try again later.");
    } finally {
      setIsResending(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center p-6">
        <Card className="w-full max-w-md shadow-2xl border-0 overflow-hidden">
          <div className="h-2 bg-gradient-to-r from-green-400 to-emerald-500" />
          <CardHeader className="text-center pb-2">
            <div className="mx-auto mb-6 w-20 h-20 rounded-full bg-green-50 flex items-center justify-center">
              <CheckCircle2 className="w-10 h-10 text-green-500" />
            </div>
            <CardTitle className="text-3xl font-bold text-gray-900">Verified!</CardTitle>
            <CardDescription className="text-lg">
              Your account is now active.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center space-y-8 p-8">
            <p className="text-gray-600">
              We're redirecting you to the login page so you can start exploring DataSpeakAI.
            </p>
            <Link to="/login" className="block">
              <Button className="w-full h-12 text-lg bg-green-600 hover:bg-green-700 transition-all shadow-lg shadow-green-200">
                Go to Login Now
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-6 group cursor-pointer" onClick={() => navigate("/")}>
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-600 to-purple-700 flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform">
              <MessageSquareCode className="w-7 h-7 text-white" />
            </div>
            <span className="font-bold text-3xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-700">
              DataSpeakAI
            </span>
          </div>
        </div>

        <Card className="shadow-2xl border-0 overflow-hidden bg-white/80 backdrop-blur-sm">
          <div className="h-2 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500" />
          <CardHeader className="text-center p-8 pb-4">
            <CardTitle className="text-2xl font-bold text-gray-900">Check your email</CardTitle>
            <CardDescription className="mt-2 text-base">
              We sent a 6-digit code to <br />
              <span className="font-semibold text-blue-600 break-all">{emailParam}</span>
            </CardDescription>
          </CardHeader>
          
          <CardContent className="p-8 pt-4 space-y-8">
            {error && (
              <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-red-600 text-sm flex items-center gap-3 animate-shake">
                <div className="w-1.5 h-1.5 bg-red-600 rounded-full flex-shrink-0" />
                {error}
              </div>
            )}
            {message && (
              <div className="p-4 bg-green-50 border border-green-100 rounded-xl text-green-600 text-sm flex items-center gap-3">
                <div className="w-1.5 h-1.5 bg-green-600 rounded-full flex-shrink-0" />
                {message}
              </div>
            )}

            <form onSubmit={handleVerify} className="space-y-8">
              <div className="flex justify-between gap-2 sm:gap-3">
                {otp.map((digit, index) => (
                  <input
                    key={index}
                    ref={(el) => (inputRefs.current[index] = el)}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOtpChange(index, e.target.value.replace(/\D/g, ""))}
                    onKeyDown={(e) => handleKeyDown(index, e)}
                    className="w-12 h-14 sm:w-14 sm:h-16 text-center text-2xl font-bold rounded-xl border-2 border-gray-100 bg-gray-50 focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100 transition-all outline-none"
                  />
                ))}
              </div>

              <Button 
                type="submit" 
                className="w-full h-14 text-lg font-semibold bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 transition-all shadow-xl shadow-blue-200" 
                disabled={isLoading}
              >
                {isLoading ? <Loader2 className="w-6 h-6 animate-spin" /> : "Verify & Continue"}
              </Button>
            </form>

            <div className="space-y-4 pt-4">
              <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                <ShieldCheck className="w-4 h-4" />
                <span>Secure verification</span>
              </div>
              <p className="text-sm text-gray-600 text-center">
                Didn't receive the code?
              </p>
              <Button 
                variant="outline" 
                className="w-full h-11 border-2 hover:bg-gray-50 transition-colors" 
                onClick={handleResend}
                disabled={isResending}
              >
                {isResending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : "Resend Code"}
              </Button>
            </div>

            <div className="pt-6 border-t border-gray-100">
              <Link to="/login">
                <Button variant="ghost" className="w-full gap-2 text-gray-500 hover:text-blue-600">
                  <ArrowLeft className="w-4 h-4" />
                  Back to Login
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
