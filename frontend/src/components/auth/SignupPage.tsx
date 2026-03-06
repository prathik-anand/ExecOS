import type { FormEvent } from "react";
import { useState } from "react";

import { useAuth } from "../../hooks/useAuth";

interface SignupPageProps {
  onNavigateLogin: () => void;
}

export default function SignupPage({ onNavigateLogin }: SignupPageProps) {
  const { signup } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!email || !password || password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      await signup({ email, password });
    } catch (err: unknown) {
      setError((err as Error).message || "Signup failed");
      setLoading(false);
    }
  };

  const inputStyle = {
    background: "var(--bg-elevated)",
    border: "1px solid var(--border)",
    color: "var(--text-primary)",
    fontSize: "14px",
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center py-12"
      style={{ background: "var(--bg-base)" }}
    >
      <div className="w-full max-w-md px-4">
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">🏛️</div>
          <h1 className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
            Join ExecOS
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
            Your Cloud C-Suite will walk you through setup
          </p>
        </div>

        <div
          className="rounded-2xl p-8"
          style={{ background: "var(--bg-surface)", border: "1px solid var(--border)" }}
        >
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="signup-email" className="block text-sm mb-1.5" style={{ color: "var(--text-secondary)" }}>
                Work email
              </label>
              <input
                id="signup-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full px-4 py-3 rounded-xl outline-none transition-all"
                style={inputStyle}
                onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
                onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                required
              />
              <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
                Business email? Your organization workspace will be created automatically.
              </p>
            </div>

            <div className="mb-5">
              <label htmlFor="signup-password" className="block text-sm mb-1.5" style={{ color: "var(--text-secondary)" }}>
                Password (min 8 chars)
              </label>
              <input
                id="signup-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-3 rounded-xl outline-none transition-all"
                style={inputStyle}
                onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
                onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                required
              />
            </div>

            {error && (
              <div
                className="mb-4 px-4 py-3 rounded-xl text-sm"
                style={{ background: "#7f1d1d22", border: "1px solid #7f1d1d", color: "#fca5a5" }}
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl font-semibold"
              style={{
                background: loading ? "var(--bg-elevated)" : "var(--accent)",
                color: "white",
                border: "none",
                cursor: loading ? "not-allowed" : "pointer",
                fontSize: "15px",
              }}
            >
              {loading ? "Creating account..." : "Create account →"}
            </button>
          </form>

          <div
            className="mt-5 text-center"
            style={{ color: "var(--text-muted)", fontSize: "13px" }}
          >
            Already have an account?{" "}
            <button
              onClick={onNavigateLogin}
              style={{
                color: "var(--accent)",
                background: "none",
                border: "none",
                cursor: "pointer",
                fontSize: "13px",
              }}
            >
              Sign in
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
