import React, { useState } from 'react';
import { AuthLayout } from '../components/auth/AuthLayout';
import { InputField } from '../components/auth/InputField';
import { PasswordField } from '../components/auth/PasswordField';
import { GlassButton } from '../components/ui/GlassButton';
import { NavigationTab } from '../types';
import { useAuth } from '../context/AuthContext';
import { User, Mail, ArrowRight, Loader2, AlertCircle } from 'lucide-react';

interface SignUpViewProps {
  onNavigate: (tab: NavigationTab) => void;
  onSuccess?: () => void;
}

export const SignUpView: React.FC<SignUpViewProps> = ({ onNavigate, onSuccess }) => {
  const { register } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState<'Student' | 'Educator' | 'General User'>('Educator');
  
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const validate = () => {
    const errs: { [key: string]: string } = {};

    if (!fullName.trim()) {
      errs.fullName = 'Full name is required.';
    }

    if (!email.trim()) {
      errs.email = 'Email address is required.';
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      errs.email = 'Please enter a valid email address.';
    }

    if (!password) {
      errs.password = 'Password is required.';
    } else if (password.length < 8) {
      errs.password = 'Password must be at least 8 characters.';
    }

    if (password !== confirmPassword) {
      errs.confirmPassword = 'Passwords do not match.';
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);

    if (!validate()) return;

    setIsLoading(true);
    try {
      const ok = await register(email.trim(), password, fullName.trim(), role);
      if (ok) {
        if (onSuccess) onSuccess();
        else onNavigate('dashboard');
      } else {
        setServerError('Registration failed. Please try with another email.');
      }
    } catch (err: any) {
      setServerError(err.response?.data?.detail || 'An error occurred during account creation.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Create your SignAura account"
      subtitle="Join the AI-powered ISL accessibility platform"
      onNavigateHome={() => onNavigate('landing')}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {serverError && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-2 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
            <span>{serverError}</span>
          </div>
        )}

        <InputField
          label="Full Name"
          type="text"
          placeholder="e.g. Rahul Sharma"
          value={fullName}
          onChange={(e) => {
            setFullName(e.target.value);
            if (errors.fullName) setErrors((prev) => ({ ...prev, fullName: '' }));
          }}
          error={errors.fullName}
          required
          icon={<User className="w-4 h-4" />}
        />

        <InputField
          label="Email"
          type="email"
          placeholder="name@example.com"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (errors.email) setErrors((prev) => ({ ...prev, email: '' }));
          }}
          error={errors.email}
          required
          autoComplete="email"
          icon={<Mail className="w-4 h-4" />}
        />

        <PasswordField
          label="Password"
          placeholder="At least 8 characters"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (errors.password) setErrors((prev) => ({ ...prev, password: '' }));
          }}
          showStrength={true}
          error={errors.password}
          required
          autoComplete="new-password"
        />

        <PasswordField
          label="Confirm Password"
          placeholder="Re-enter password"
          value={confirmPassword}
          onChange={(e) => {
            setConfirmPassword(e.target.value);
            if (errors.confirmPassword) setErrors((prev) => ({ ...prev, confirmPassword: '' }));
          }}
          error={errors.confirmPassword}
          required
          autoComplete="new-password"
        />

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
            {isLoading ? 'Creating Account...' : 'Create Account'}
          </GlassButton>
        </div>

        {/* Signin Redirect Link */}
        <div className="text-center pt-3 border-t border-[#273154]">
          <p className="text-xs text-[#A8B2D1]">
            Already have an account?{' '}
            <button
              type="button"
              onClick={() => onNavigate('signin')}
              className="text-white font-semibold hover:text-[#22D3EE] transition-colors ml-1 focus:outline-none"
            >
              Sign In
            </button>
          </p>
        </div>
      </form>
    </AuthLayout>
  );
};
