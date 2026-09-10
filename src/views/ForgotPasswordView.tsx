import React, { useState } from 'react';
import { AuthLayout } from '../components/auth/AuthLayout';
import { InputField } from '../components/auth/InputField';
import { GlassButton } from '../components/ui/GlassButton';
import { NavigationTab } from '../types';
import { Mail, ArrowLeft, Send, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

interface ForgotPasswordViewProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const ForgotPasswordView: React.FC<ForgotPasswordViewProps> = ({ onNavigate }) => {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !/\S+@\S+\.\S+/.test(email)) {
      setError('Please enter a valid email address.');
      return;
    }

    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      setIsSubmitted(true);
    }, 800);
  };

  return (
    <AuthLayout
      title="Reset your password"
      subtitle="Enter your email to receive recovery instructions"
      onNavigateHome={() => onNavigate('landing')}
    >
      {isSubmitted ? (
        <div className="space-y-5 text-center py-3">
          <div className="w-12 h-12 rounded-xl bg-[#22D3EE]/15 border border-[#22D3EE]/30 flex items-center justify-center mx-auto text-[#22D3EE]">
            <CheckCircle2 className="w-6 h-6" />
          </div>

          <div className="space-y-1.5">
            <h3 className="text-lg font-bold text-white">Reset link requested</h3>
            <p className="text-xs text-[#A8B2D1] leading-relaxed max-w-sm mx-auto">
              If an account exists for <span className="text-white font-semibold">{email}</span>, password reset instructions have been dispatched.
            </p>
          </div>

          <GlassButton
            variant="primary"
            size="md"
            onClick={() => onNavigate('signin')}
            className="w-full justify-center"
            icon={<ArrowLeft className="w-4 h-4 text-[#080D24]" />}
          >
            Back to Sign In
          </GlassButton>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-2 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <InputField
            label="Email"
            type="email"
            placeholder="name@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            icon={<Mail className="w-4 h-4" />}
          />

          <div className="pt-2 space-y-3">
            <GlassButton
              type="submit"
              variant="primary"
              size="lg"
              className="w-full justify-center text-sm font-bold"
              disabled={isLoading}
              icon={isLoading ? <Loader2 className="w-4 h-4 animate-spin text-[#080D24]" /> : <Send className="w-4 h-4 text-[#080D24]" />}
            >
              {isLoading ? 'Processing...' : 'Send Reset Link'}
            </GlassButton>

            <button
              type="button"
              onClick={() => onNavigate('signin')}
              className="w-full text-center text-xs text-[#A8B2D1] hover:text-white flex items-center justify-center gap-1.5 py-1 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Sign In</span>
            </button>
          </div>
        </form>
      )}
    </AuthLayout>
  );
};
