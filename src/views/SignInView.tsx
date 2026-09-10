import React, { useState } from 'react';
import { AuthLayout } from '../components/auth/AuthLayout';
import { InputField } from '../components/auth/InputField';
import { PasswordField } from '../components/auth/PasswordField';
import { GlassButton } from '../components/ui/GlassButton';
import { NavigationTab } from '../types';
import { useAuth } from '../context/AuthContext';
import { Mail, ArrowRight, Loader2, AlertCircle } from 'lucide-react';

interface SignInViewProps {
  onNavigate: (tab: NavigationTab) => void;
  onSuccess?: () => void;
}

export const SignInView: React.FC<SignInViewProps> = ({ onNavigate, onSuccess }) => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!email.trim() || !password.trim()) {
      setErrorMessage('Please enter both your email address and password.');
      return;
    }

    setIsLoading(true);
    try {
      const ok = await login(email.trim(), password);
      if (ok) {
        if (onSuccess) onSuccess();
        else onNavigate('dashboard');
      } else {
        setErrorMessage('Invalid credentials. Please verify your email and password.');
      }
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Sign in failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to your SignAura account"
      onNavigateHome={() => onNavigate('landing')}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMessage && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-2 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
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

        <PasswordField
          label="Password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />

        {/* Options Row */}
        <div className="flex items-center justify-between text-xs pt-1">
          <label className="flex items-center gap-2 text-[#A8B2D1] cursor-pointer select-none">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="rounded bg-[#101735] border-[#273154] text-[#22D3EE] focus:ring-[#22D3EE]/30"
            />
            <span>Remember me</span>
          </label>

          <button
            type="button"
            onClick={() => onNavigate('forgot-password')}
            className="text-[#22D3EE] hover:text-[#38BDF8] font-medium hover:underline focus:outline-none"
          >
            Forgot password?
          </button>
        </div>

        {/* Submit Action */}
        <div className="pt-2">
          <GlassButton
            type="submit"
            variant="primary"
            size="lg"
            className="w-full justify-center text-sm font-bold"
            disabled={isLoading}
            icon={isLoading ? <Loader2 className="w-4 h-4 animate-spin text-[#080D24]" /> : <ArrowRight className="w-4 h-4 text-[#080D24]" />}
            iconPosition="right"
          >
            {isLoading ? 'Signing In...' : 'Sign In'}
          </GlassButton>
        </div>

        {/* Signup Redirect Link */}
        <div className="text-center pt-3 border-t border-[#273154]">
          <p className="text-xs text-[#A8B2D1]">
            Don't have an account?{' '}
            <button
              type="button"
              onClick={() => onNavigate('signup')}
              className="text-white font-semibold hover:text-[#22D3EE] transition-colors ml-1 focus:outline-none"
            >
              Create account
            </button>
          </p>
        </div>
      </form>
    </AuthLayout>
  );
};
