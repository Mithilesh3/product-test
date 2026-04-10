import "../styles/Footer.css";

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-video-bg">
        <video autoPlay muted loop playsInline>
          <source src="/Seven Chakras.mp4" type="video/mp4" />
        </video>
      </div>

      <div className="footer-about">
        <h2 className="footer-about-heading">About LifeSignify</h2>

        <div className="footer-about-copy">
          <p>
            LifeSignify NumAI is an AI-powered spiritual intelligence platform that combines ancient Vedic
            wisdom, numerology, and astrology with modern artificial intelligence. Our mission is to help
            individuals discover clarity, balance, and purpose in their lives.
          </p>

          <p>
            Through advanced numerology analysis, AI-driven insights, and traditional Vedic knowledge, we
            provide personalized guidance for career decisions, relationships, business success, and life
            growth.
          </p>

          <p>
            From AI-powered numerology reports to muhurat guidance, spiritual rituals, gemstones, and sacred
            yantras, LifeSignify creates a complete spiritual ecosystem for seekers across India and around
            the world.
          </p>
        </div>

        <div className="footer-youtube-section">
          <p className="footer-youtube-title">Watch LifeSignify on YouTube</p>
          <a
            href="https://www.youtube.com/@LifeSignify"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-youtube-link"
          >
            https://www.youtube.com/@LifeSignify
          </a>

          <div className="footer-youtube-grid">
            <div className="footer-youtube-frame-wrap">
              <iframe
                width="424"
                height="238"
                src="https://www.youtube.com/embed/xn-2Vuk2yyE"
                title="Brain Problems का समाधान सिर्फ 10 मिनट में | 5 Easy Neuro Therapy Exercises"
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                referrerPolicy="strict-origin-when-cross-origin"
                allowFullScreen
              />
            </div>

            <div className="footer-youtube-frame-wrap">
              <iframe
                width="1383"
                height="494"
                src="https://www.youtube.com/embed/EQ9pRu1I1Dc"
                title="ॐ का रहस्य | ॐ कोई मंत्र नहीं है | स्वास्थ्य और समृद्धि का मार्ग है"
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                referrerPolicy="strict-origin-when-cross-origin"
                allowFullScreen
              />
            </div>
          </div>
        </div>
      </div>

      <hr className="footer-divider" />

      <div className="footer-grid">
        <div className="footer-col">
          <h4>Vedic AI Intelligence</h4>
          <ul>
            <li>Name Numerology Correction</li>
            <li>Business Name Numerology</li>
            <li>Mobile Number Numerology</li>
            <li>Vehicle Number Numerology</li>
            <li>House Number Numerology</li>
            <li>Signature Numerology</li>
            <li>Birth Chart Analysis</li>
            <li>Kundli Matching</li>
            <li>Career Prediction</li>
            <li>Love & Relationship Prediction</li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Muhurat and Rituals Intelligence</h4>
          <ul>
            <li>Marriage Muhurat</li>
            <li>Griha Pravesh Muhurat</li>
            <li>Naamkaran Muhurat</li>
            <li>Mundan Muhurat</li>
            <li>Car / Bike Muhurat</li>
            <li>Bhoomi Pujan Muhurat</li>
            <li>Business Opening Muhurat</li>
            <li>Maha Mrityunjaya Jaap</li>
            <li>Rudra Abhishek</li>
            <li>Navgraha Shanti</li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Spiritual Store Intelligence</h4>
          <ul>
            <li>Rudraksha</li>
            <li>Rudraksha Mala</li>
            <li>Rudraksha Bracelet</li>
            <li>Blue Sapphire (Neelam)</li>
            <li>Yellow Sapphire (Pukhraj)</li>
            <li>Emerald (Panna)</li>
            <li>Ruby (Manik)</li>
            <li>Shree Yantra</li>
            <li>Navgraha Yantra</li>
            <li>Money Magnet Bracelet</li>
          </ul>
        </div>

        <div className="footer-col">
          <h4>Contact and Trust</h4>

          <p>We are available 24x7 on chat support</p>

          <p className="support-mail">support@lifesignify.ai</p>

          <div className="social-icons">
            <a href="https://www.facebook.com/lifesignify" target="_blank" rel="noopener noreferrer">
              <i className="fab fa-facebook-f" />
            </a>

            <a href="https://www.instagram.com/lifesignify/" target="_blank" rel="noopener noreferrer">
              <i className="fab fa-instagram" />
            </a>

            <a href="https://www.youtube.com/@LifeSignify" target="_blank" rel="noopener noreferrer">
              <i className="fab fa-youtube" />
            </a>
          </div>

          <div className="trust-badges">
            <span>Private & Confidential</span>
            <span>Verified Astrology</span>
            <span>Secure Payments</span>
          </div>
        </div>
      </div>

      <div className="ai-tools">
        <h4>AI Tools Intelligence</h4>
        <ul>
          <li>Live Astrologer Chat</li>
          <li>AI Numerology Report</li>
          <li>Compatibility AI</li>
        </ul>
      </div>

      <div className="footer-bottom">© 2026 LifeSignify NumAI — All Rights Reserved</div>
    </footer>
  );
}

