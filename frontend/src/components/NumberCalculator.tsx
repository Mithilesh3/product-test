import "../styles/NumberCalculator.css";
import { useState } from "react";

export default function NumberCalculator() {

  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [result, setResult] = useState<number | null>(null);

  const reduceNumber = (num: number): number => {
    while (num > 9) {
      num = num.toString().split("").reduce((a, b) => a + Number(b), 0);
    }
    return num;
  };

  const calculateNumber = () => {
    if (!dob) return;

    const digits = dob.replaceAll("-", "").split("");
    const sum = digits.reduce((a, b) => a + Number(b), 0);

    setResult(reduceNumber(sum));
  };

  return (
    <section className="number-section">

      {/* 🔥 ADD THIS WRAPPER */}
      <div className="num-card">

        <h2>🔢 Discover Your Destiny Number</h2>

        <p className="num-sub">
          Enter your details to unlock your life path insights
        </p>

        <div className="num-form">

          <input
            type="text"
            placeholder="Enter Your Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <input
            type="date"
            value={dob}
            onChange={(e) => setDob(e.target.value)}
          />

          <button onClick={calculateNumber}>
            Calculate
          </button>

        </div>

        {result && (
          <div className="num-result">
            <h3>Your Number: {result}</h3>

            <p>
              {result === 1 && "Leader, independent, ambitious 🔥"}
              {result === 2 && "Peaceful, emotional, cooperative 🌙"}
              {result === 3 && "Creative, expressive, joyful 🎨"}
              {result === 4 && "Hardworking, disciplined, practical 🏗️"}
              {result === 5 && "Freedom-loving, adventurous 🌍"}
              {result === 6 && "Caring, responsible, loving ❤️"}
              {result === 7 && "Spiritual, analytical, deep thinker 🧘"}
              {result === 8 && "Powerful, success-driven 💼"}
              {result === 9 && "Compassionate, humanitarian 🌟"}
            </p>
          </div>
        )}

      </div>

    </section>
  );
}