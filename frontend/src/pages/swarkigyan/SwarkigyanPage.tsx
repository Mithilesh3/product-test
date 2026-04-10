import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import toast from "react-hot-toast";

import {
  sendSwarChat,
  type SwarHistoryMessage,
  type SwarLanguage,
} from "../../services/swarkigyanService";

interface UiMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
}

type SpeechRecognitionInstance = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
};

interface SpeechRecognitionResultLike {
  transcript: string;
}

interface SpeechRecognitionEventLike {
  results: ArrayLike<ArrayLike<SpeechRecognitionResultLike>>;
}

interface SpeechRecognitionCtor {
  new (): SpeechRecognitionInstance;
}

declare global {
  interface Window {
    webkitSpeechRecognition?: SpeechRecognitionCtor;
    SpeechRecognition?: SpeechRecognitionCtor;
  }
}

const LANGUAGE_OPTIONS: { value: SwarLanguage; label: string }[] = [
  { value: "auto", label: "Auto" },
  { value: "english", label: "English" },
  { value: "hindi", label: "Hindi" },
  { value: "hinglish", label: "Hinglish" },
];

const SWAR_PANEL_NOTE =
  "स्वर विज्ञान को सरल रूप में समझें। नीचे दिया गया वीडियो देखें, फिर अपना प्रश्न चैट में लिखें या माइक्रोफ़ोन से बोलकर भेजें।";

const VOICE_LANG_MAP: Record<SwarLanguage, string> = {
  auto: "hi-IN",
  hindi: "hi-IN",
  english: "en-US",
  hinglish: "hi-IN",
};

export default function SwarkigyanPage() {
  const [language, setLanguage] = useState<SwarLanguage>("auto");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [messages, setMessages] = useState<UiMessage[]>([
    {
      id: "init-assistant",
      role: "assistant",
      text: "",
    },
  ]);

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);

  const history = useMemo<SwarHistoryMessage[]>(
    () =>
      messages
        .filter((m) => m.id !== "init-assistant")
        .slice(-8)
        .map((m) => ({ role: m.role, content: m.text })),
    [messages],
  );

  const renderInitialAssistantMessage = () => (
    <div className="space-y-3">
      <p>नमस्ते 🙏</p>
      <p>
        मैं आपका <strong>स्वर मार्गदर्शक</strong> हूँ — स्वर विज्ञान के ज्ञान और{" "}
        <strong>आचार्य रवि शंकर जी</strong> की शिक्षाओं से प्रेरित।
      </p>
      <p>
        आपकी श्वास — इड़ा, पिंगला और सुषुम्ना के माध्यम से — हर क्षण आपको दिशा देती है।
        मुझसे सिर्फ <em>क्या करना है</em> मत पूछिए… मुझसे पूछिए <em>कब करना है</em>।
      </p>
      <p>
        <strong>अभ्यास के लिए आचार्य जी के मार्गदर्शन से अवश्य जुड़ें।</strong>
      </p>
      <p>और फिर उसे अपने जीवन में प्रयोग करें।</p>
      <p>श्वास को समझ लीजिए… समय आपके पक्ष में आ जाएगा।</p>
    </div>
  );

  const handleSend = async (e: FormEvent) => {
    e.preventDefault();
    const message = input.trim();
    if (!message || loading) return;

    const userMessage: UiMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      text: message,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await sendSwarChat({
        message,
        language_preference: language,
        history: [...history, { role: "user", content: message }],
      });

      const assistantMessage: UiMessage = {
        id: `a-${Date.now()}`,
        role: "assistant",
        text: response.reply,
      };
      setMessages((prev) => [...prev, assistantMessage]);

      if (response.warning_count > 0) {
        toast.error(`Warning ${response.warning_count}/3: abusive language is not allowed.`);
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "SwarPrana AI is not reachable right now.");
    } finally {
      setLoading(false);
    }
  };

  const stopRecording = () => {
    const rec = recognitionRef.current;
    if (!rec) return;
    rec.stop();
    setIsRecording(false);
  };

  const startRecording = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      toast.error("Voice input is not supported in this browser.");
      return;
    }

    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = VOICE_LANG_MAP[language];
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (event: SpeechRecognitionEventLike) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript || "")
        .join(" ")
        .trim();
      if (transcript) {
        setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
      }
    };

    recognition.onend = () => {
      setIsRecording(false);
    };

    recognition.onerror = () => {
      setIsRecording(false);
      toast.error("Voice capture failed. Please try again.");
    };

    recognitionRef.current = recognition;
    setIsRecording(true);
    recognition.start();
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
      return;
    }
    startRecording();
  };

  useEffect(
    () => () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    },
    [],
  );

  return (
    <div className="min-h-[70vh] rounded-2xl border border-gray-800 bg-gray-950 p-3 text-white sm:p-4 md:p-5 lg:h-[calc(100dvh-9rem)] lg:max-h-[calc(100dvh-9rem)] lg:overflow-hidden">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight md:text-3xl">SwarPrana AI</h1>
          <p className="text-gray-400 mt-1">Swar Vigyan guidance assistant for breath awareness and swara timing.</p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Language</span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as SwarLanguage)}
            className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
            disabled={loading || isRecording}
          >
            {LANGUAGE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid min-h-0 grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3 lg:h-[calc(100%-5.25rem)]">
        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-3 sm:p-4 min-h-[220px] lg:min-h-0 lg:flex lg:flex-col xl:col-span-1">
          <div className="space-y-4 overflow-auto pr-1">
            <h2 className="text-xl font-semibold">स्वर मार्गदर्शन</h2>
            <p className="text-sm text-gray-300 leading-6">{SWAR_PANEL_NOTE}</p>
            <div className="rounded-xl border border-indigo-700/40 bg-gray-950/50 p-2">
              <iframe
                width="1383"
                height="494"
                src="https://www.youtube.com/embed/ianUv_ehTOw"
                title="स्वर विज्ञान से जीवन में क्या चमत्कार हो सकते हैं | जीवन में प्रयोग कैसे करें"
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                referrerPolicy="strict-origin-when-cross-origin"
                allowFullScreen
                className="w-full aspect-video rounded-lg"
              />
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-3 sm:p-4 lg:flex lg:min-h-0 lg:flex-col xl:col-span-2">
          <div className="space-y-3 pr-1 lg:flex-1 lg:overflow-auto">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`max-w-full rounded-xl px-3 py-2.5 whitespace-pre-wrap text-sm leading-6 sm:max-w-[90%] sm:px-4 sm:py-3 ${
                  msg.role === "assistant"
                    ? "bg-indigo-950/70 border border-indigo-800 text-indigo-100"
                    : "bg-gray-800 border border-gray-700 text-gray-100 ml-auto"
                }`}
              >
                {msg.id === "init-assistant" ? renderInitialAssistantMessage() : msg.text}
              </div>
            ))}
          </div>

          <form onSubmit={handleSend} className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto_auto]">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask SwarPrana AI..."
              className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-indigo-500"
              disabled={loading}
            />

            <button
              type="button"
              onClick={toggleRecording}
              disabled={loading}
              className={`px-4 py-3 rounded-lg font-medium border ${
                isRecording
                  ? "bg-red-600/20 border-red-500 text-red-200"
                  : "bg-gray-900 border-gray-700 text-gray-200 hover:border-indigo-500"
              }`}
            >
              {isRecording ? "Stop Mic" : "Mic"}
            </button>

            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-5 py-3 rounded-lg font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60"
            >
              {loading ? "Sending..." : "Send"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
