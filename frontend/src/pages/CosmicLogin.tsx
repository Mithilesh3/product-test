import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import { useAuth } from "../context/AuthContext";
import DhyanamSection from "../components/DhyanamSection";
import NumberCalculator from "../components/NumberCalculator";
import Footer from "../components/Footer";
import logo from "../assets/logo.png";
import "../styles/cosmic-login.css";
import "../styles/cosmic-responsive.css";
import "../styles/section-seam-fix.css";

export default function CosmicLogin() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const introVideoId = "6NHbaLAXXPk";
  const [introFrozen, setIntroFrozen] = useState(false);
  const introVideoSrc = `https://www.youtube.com/embed/${introVideoId}?autoplay=${introFrozen ? 0 : 1}&controls=0&modestbranding=1&rel=0&playsinline=1&mute=0`;

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      navigate("/dashboard");
    }
  }, [user, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;

    if (!identifier.trim() || !password) {
      toast.error("Please enter mobile number and password");
      return;
    }

    setLoading(true);
    try {
      await login(identifier.trim(), password);
      toast.success("Welcome back");
      navigate("/dashboard");
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <main className="auth-cosmic-shell auth-page">
        <div className="solar-system-bg">
          <div className="solar-stars-layer"></div>
          <div className="solar-nebula"></div>

          <div className="solar-particles-layer">
            <div className="solar-particle solar-particle-1"></div>
            <div className="solar-particle solar-particle-2"></div>
            <div className="solar-particle solar-particle-3"></div>
            <div className="solar-particle solar-particle-4"></div>
            <div className="solar-particle solar-particle-5"></div>
            <div className="solar-particle solar-particle-6"></div>
            <div className="solar-particle solar-particle-7"></div>
            <div className="solar-particle solar-particle-8"></div>
          </div>

          <div className="numerology-floaters">
            <span className="numerology-digit digit-1">1</span>
            <span className="numerology-digit digit-2">2</span>
            <span className="numerology-digit digit-3">3</span>
            <span className="numerology-digit digit-4">4</span>
            <span className="numerology-digit digit-5">9</span>
          </div>

          <div className="solar-core"></div>
          <div className="solar-orbit solar-orbit-1">
            <span className="solar-planet solar-planet-1"></span>
          </div>
          <div className="solar-orbit solar-orbit-2">
            <span className="solar-planet solar-planet-2"></span>
          </div>
          <div className="solar-orbit solar-orbit-3">
            <span className="solar-planet solar-planet-3"></span>
          </div>
          <div className="solar-orbit solar-orbit-4">
            <span className="solar-planet solar-planet-4"></span>
          </div>
          <div className="solar-orbit solar-orbit-5">
            <span className="solar-planet solar-planet-5"></span>
          </div>

          <div className="solar-planet-large solar-planet-jupiter"></div>
          <div className="solar-planet-large solar-planet-saturn"></div>
          <div className="solar-planet-large solar-planet-earth"></div>
          <div className="solar-planet-large solar-planet-ice"></div>
          <div className="solar-constellation solar-constellation-top"></div>
          <div className="solar-constellation solar-constellation-bottom"></div>
          <div className="solar-comet"></div>
        </div>

        <div className="auth-shell-right">
          <div className="auth-brand-card brand-header">
            <img src={logo} className="brand-logo" alt="LifeSignify Logo" />
            <span className="auth-brand-title">LifeSignify AnkAI</span>
          </div>

          <div className="auth-login-panel auth-glass-panel">
            <div className="auth-header">
              <p className="auth-kicker">Member Access</p>
              <span className="auth-badge">Secure</span>
            </div>

            <h2 className="auth-heading auth-card-title">Sign in</h2>
            <p className="auth-subtitle">
              Enter your credentials to access your numerology workspace.
            </p>

            <form className="auth-form" onSubmit={handleSubmit}>
              <label className="field-label">Phone Number</label>
              <input
                className="auth-input"
                placeholder="+91 9876543210"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
              />

              <label className="field-label">Password</label>
              <input
                className="auth-input"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />

              <button className="auth-button" type="submit" disabled={loading}>
                {loading ? "Logging in..." : "Login"}
              </button>

              <Link to="/register" className="auth-create-btn">
                Create an account
              </Link>
            </form>
          </div>
        </div>

        <div className="auth-om-symbol">ॐ</div>

        <button
          type="button"
          className="auth-om-freeze-btn"
          onClick={() => setIntroFrozen((prev) => !prev)}
        >
          {introFrozen ? "चलाएँ" : "स्थिर (Freez)"}
        </button>

        <div className="auth-om-audio-source" aria-hidden="true">
          <iframe
            width="1383"
            height="494"
            src={introVideoSrc}
            title="Embarking on the Journey: Why I Started Life Signify"
            frameBorder="0"
            allow="autoplay; accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            referrerPolicy="strict-origin-when-cross-origin"
            allowFullScreen
          />
        </div>
      </main>

      <DhyanamSection />
      <NumberCalculator />
      <Footer />

      <a
        href="https://wa.me/919876543210"
        className="whatsapp-float"
        target="_blank"
        rel="noreferrer"
      >
        WhatsApp
      </a>
    </>
  );
}
