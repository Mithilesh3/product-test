import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { useAuth } from "../../context/AuthContext";
import {
  applyKnowledgeAsset,
  fetchKnowledgeAssets,
  processKnowledgeAsset,
  rejectKnowledgeAsset,
  uploadKnowledgeAsset,
  type KnowledgeAsset,
} from "../../services/adminService";

type UploadState = {
  title: string;
  description: string;
  language: string;
  sourceType: string;
  domain: string;
  file: File | null;
  manualNotes: string;
};

export default function AdminKnowledgePage() {
  const { user } = useAuth();
  const [assets, setAssets] = useState<KnowledgeAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaChunksRef = useRef<Blob[]>([]);
  const [form, setForm] = useState<UploadState>({
    title: "",
    description: "",
    language: "hindi",
    sourceType: "pdf",
    domain: "numerology",
    file: null,
    manualNotes: "",
  });

  const isSuperAdmin = user?.role === "super_admin";

  useEffect(() => {
    return () => {
      if (recordedUrl) {
        URL.revokeObjectURL(recordedUrl);
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    };
  }, [recordedUrl]);

  const loadAssets = async () => {
    try {
      const data = await fetchKnowledgeAssets();
      setAssets(data);
    } catch {
      toast.error("Unable to load knowledge assets.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isSuperAdmin) {
      loadAssets();
    }
  }, [isSuperAdmin]);

  const resolveAudioMimeType = () => {
    if (!("MediaRecorder" in window)) return "";
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/ogg",
    ];
    return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
  };

  const handleStartRecording = async () => {
    if (isRecording) return;
    if (!navigator.mediaDevices?.getUserMedia) {
      toast.error("Audio recording is not supported in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = resolveAudioMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

      mediaChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          mediaChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(mediaChunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        if (recordedUrl) {
          URL.revokeObjectURL(recordedUrl);
        }
        const url = URL.createObjectURL(blob);
        setRecordedUrl(url);

        const extension = recorder.mimeType.includes("ogg") ? "ogg" : "webm";
        const filename = `voice-note-${Date.now()}.${extension}`;
        const file = new File([blob], filename, { type: blob.type });

        setForm((prev) => ({
          ...prev,
          file,
          sourceType: "audio",
        }));

        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error(error);
      toast.error("Microphone access denied or unavailable.");
    }
  };

  const handleStopRecording = () => {
    if (!mediaRecorderRef.current) return;
    if (mediaRecorderRef.current.state === "inactive") return;
    mediaRecorderRef.current.stop();
    setIsRecording(false);
  };

  const handleClearRecording = () => {
    if (recordedUrl) {
      URL.revokeObjectURL(recordedUrl);
    }
    setRecordedUrl(null);
    setForm((prev) => ({ ...prev, file: null }));
  };

  const handleUpload = async () => {
    if (!form.file) {
      toast.error("Please select or record a PDF/audio file.");
      return;
    }
    const data = new FormData();
    data.append("file", form.file);
    if (form.title) data.append("title", form.title);
    if (form.description) data.append("description", form.description);
    if (form.language) data.append("language", form.language);
    if (form.domain) data.append("domain", form.domain);
    if (form.sourceType) data.append("source_type", form.sourceType);
    if (form.manualNotes) data.append("manual_notes", form.manualNotes);

    setUploading(true);
    try {
      await uploadKnowledgeAsset(data);
      toast.success("Asset uploaded. Processing started.");
      setForm((prev) => ({ ...prev, file: null, title: "", description: "", manualNotes: "" }));
      await loadAssets();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleProcess = async (id: number) => {
    try {
      await processKnowledgeAsset(id);
      toast.success("Re-processing started.");
      await loadAssets();
    } catch {
      toast.error("Unable to process asset.");
    }
  };

  const handleApply = async (id: number) => {
    try {
      const consent = window.confirm(
        "Apply deterministic updates now? This will update the live knowledge store.",
      );
      if (!consent) return;
      const notes = window.prompt("Optional approval notes (leave blank to skip)") || "";
      await applyKnowledgeAsset(id, notes);
      toast.success("Deterministic updates applied.");
      await loadAssets();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Apply failed");
    }
  };

  const handleReject = async (id: number) => {
    try {
      const reason = window.prompt("Reason for rejection (optional)") || "";
      await rejectKnowledgeAsset(id, reason);
      toast.success("Asset rejected.");
      await loadAssets();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Reject failed");
    }
  };

  if (!isSuperAdmin) {
    return (
      <div className="rounded-2xl border border-rose-800/40 bg-rose-500/10 p-6 text-sm text-rose-200">
        Super admin access required. This area is restricted to knowledge enrichment.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-gray-800 bg-gradient-to-r from-gray-900 to-gray-950 p-6">
        <p className="text-xs uppercase tracking-[0.18em] text-indigo-300">
          Super Admin Knowledge Studio
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-white">
          Deterministic Enrichment Console
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-gray-300">
          Upload PDFs or voice notes (Hindi / English). Select Numerology or Swar Vigyan
          so the system extracts the right knowledge. Apply updates after reviewing the
          extraction quality.
        </p>
      </div>

      <div className="rounded-2xl border border-gray-800 bg-gray-900 p-5">
        <h2 className="text-lg font-semibold text-white">Upload Knowledge Asset</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <input
            className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-200"
            placeholder="Title (optional)"
            value={form.title}
            onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
          />
          <select
            className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-200"
            value={form.language}
            onChange={(e) => setForm((prev) => ({ ...prev, language: e.target.value }))}
          >
            <option value="hindi">Hindi</option>
            <option value="english">English</option>
            <option value="bilingual">Bilingual</option>
          </select>
          <select
            className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-200"
            value={form.domain}
            onChange={(e) => setForm((prev) => ({ ...prev, domain: e.target.value }))}
          >
            <option value="numerology">Numerology</option>
            <option value="swar_vigyan">Swar Vigyan</option>
          </select>
          <select
            className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-200"
            value={form.sourceType}
            onChange={(e) => setForm((prev) => ({ ...prev, sourceType: e.target.value }))}
          >
            <option value="pdf">PDF</option>
            <option value="audio">Audio</option>
            <option value="text">Text</option>
          </select>
          <input
            className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-200"
            placeholder="Description (optional)"
            value={form.description}
            onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
          />
          <input
            type="file"
            className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-200"
            accept={form.sourceType === "audio" ? "audio/*" : form.sourceType === "pdf" ? "application/pdf" : undefined}
            onChange={(e) => {
              const file = e.target.files?.[0] || null;
              setForm((prev) => ({ ...prev, file }));
              if (file && recordedUrl) {
                URL.revokeObjectURL(recordedUrl);
                setRecordedUrl(null);
              }
            }}
          />
          <textarea
            className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-200 md:col-span-2"
            rows={3}
            placeholder="Optional manual guidance (one point per line)"
            value={form.manualNotes}
            onChange={(e) => setForm((prev) => ({ ...prev, manualNotes: e.target.value }))}
          />
        </div>

        <div className="mt-4 rounded-xl border border-gray-800 bg-gray-950 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-white">Record Voice Note</p>
              <p className="text-xs text-gray-400">
                Use your microphone to record guidance. Audio transcription requires
                <span className="text-gray-200"> AZURE_OPENAI_AUDIO_DEPLOYMENT</span>.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-lg border border-indigo-500/60 px-3 py-1.5 text-xs text-indigo-200 hover:bg-indigo-500/10 disabled:opacity-50"
                onClick={handleStartRecording}
                disabled={isRecording}
              >
                {isRecording ? "Recording..." : "Start Recording"}
              </button>
              <button
                type="button"
                className="rounded-lg border border-rose-500/60 px-3 py-1.5 text-xs text-rose-200 hover:bg-rose-500/10 disabled:opacity-50"
                onClick={handleStopRecording}
                disabled={!isRecording}
              >
                Stop
              </button>
              <button
                type="button"
                className="rounded-lg border border-gray-700 px-3 py-1.5 text-xs text-gray-200 hover:bg-gray-800"
                onClick={handleClearRecording}
                disabled={!recordedUrl}
              >
                Clear
              </button>
            </div>
          </div>

          {recordedUrl ? (
            <div className="mt-3">
              <audio controls src={recordedUrl} className="w-full" />
              <p className="mt-2 text-xs text-gray-400">
                Recorded file is attached for upload.
              </p>
            </div>
          ) : (
            <p className="mt-3 text-xs text-gray-500">
              No recording yet. Click Start Recording to capture a voice note.
            </p>
          )}
        </div>

        <button
          className="mt-4 rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600 disabled:opacity-60"
          onClick={handleUpload}
          disabled={uploading}
        >
          {uploading ? "Uploading..." : "Upload & Process"}
        </button>
      </div>

      <div className="rounded-2xl border border-gray-800 bg-gray-900 p-5">
        <h2 className="text-lg font-semibold text-white">Uploaded Assets</h2>
        {loading ? (
          <p className="mt-4 text-sm text-gray-400">Loading assets...</p>
        ) : assets.length ? (
          <div className="mt-4 space-y-3">
            {assets.map((asset) => (
              <div
                key={asset.id}
                className="flex flex-col gap-3 rounded-xl border border-gray-800 bg-gray-950 p-4 md:flex-row md:items-center md:justify-between"
              >
                <div>
                  <p className="text-sm font-semibold text-white">
                    {asset.title || "Untitled Asset"}
                  </p>
                  <p className="text-xs text-gray-400">
                    {(asset.domain || "numerology").replace("_", " ")} | {asset.source_type.toUpperCase()} | {asset.language || "unknown"} | {asset.status}
                    {asset.approval_status ? ` | approval: ${asset.approval_status}` : ""}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    className="rounded-lg border border-gray-700 px-3 py-1.5 text-xs text-gray-200 hover:bg-gray-800"
                    onClick={() => handleProcess(asset.id)}
                  >
                    Reprocess
                  </button>
                  <button
                    className="rounded-lg border border-indigo-500/60 px-3 py-1.5 text-xs text-indigo-300 hover:bg-indigo-500/10 disabled:opacity-50"
                    onClick={() => handleApply(asset.id)}
                    disabled={!asset.has_updates}
                  >
                    Apply Updates
                  </button>
                  <button
                    className="rounded-lg border border-rose-500/60 px-3 py-1.5 text-xs text-rose-300 hover:bg-rose-500/10"
                    onClick={() => handleReject(asset.id)}
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm text-gray-400">No knowledge assets uploaded yet.</p>
        )}
      </div>
    </div>
  );
}
