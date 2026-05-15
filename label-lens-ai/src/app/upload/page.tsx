"use client";

import { useState, useEffect } from "react";
import Layout from "../components/Layout";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [textPreview, setTextPreview] = useState<string | null>(null);

  useEffect(() => {
    if (file && file.type === "text/plain") {
      const reader = new FileReader();
      reader.onload = () => setTextPreview(reader.result as string);
      reader.readAsText(file);
    } else {
      setTextPreview(null);
    }
  }, [file]);

  const handleFile = async () => {
    if (!file) {
      setError("No file selected.");
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/extract/analyze-document", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error(`HTTP error ${res.status}`);

      const result = await res.json();
      setData(result);
    } catch (err: any) {
      console.error("Upload failed:", err);
      setError(err.message || "Upload failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="min-h-screen px-6 py-10 bg-white text-slate-800">
        <h1 className="text-4xl font-bold mb-8 text-left">Generate Compliance Report</h1>

        <div className="flex flex-col lg:flex-row gap-10">
          {/* Left Panel: Upload + Results */}
          <div className="lg:w-2/3 space-y-10">
            {/* Upload Box */}
            <div className="border border-slate-300 bg-slate-50 p-6 rounded-md shadow">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <button
                  onClick={() => document.getElementById("hiddenFile")?.click()}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium"
                >
                  Choose File
                </button>

                <input
                  id="hiddenFile"
                  type="file"
                  accept=".pdf,.docx,image/*"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="hidden"
                />

                {file && (
                  <p className="text-sm text-slate-600">
                    Selected: <span className="font-medium">{file.name}</span>
                  </p>
                )}
              </div>

              <button
                onClick={handleFile}
                className="mt-4 w-full sm:w-auto px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium"
              >
                Upload & Analyze
              </button>

              {loading && (
                <p className="text-blue-600 mt-4 animate-pulse flex items-center gap-2">
                  <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Analyzing file...
                </p>
              )}

              {error && <p className="text-red-600 mt-2 font-semibold">❌ {error}</p>}
            </div>

            {/* Results */}
            {data && (
              <div className="space-y-8">
                <ResultSection title="Document Info">
                  <pre className="bg-slate-100 p-4 rounded text-sm overflow-x-auto">
                    {JSON.stringify(data.document_info, null, 2)}
                  </pre>
                </ResultSection>

                <ResultSection title="Claims">
                  {data.claims?.length ? (
                    <ul className="space-y-2">
                      {data.claims.map((claim: any, i: number) => (
                        <li key={i} className="bg-white border rounded p-3 shadow-sm">
                          <p className="font-medium">{claim.claim_text}</p>
                          <p className="text-sm text-slate-600 mt-1">Type: {claim.claim_type}</p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-slate-600 italic">No claims found.</p>
                  )}
                </ResultSection>

                <ResultSection title="Ingredients">
                  {data.ingredients?.length ? (
                    <ul className="space-y-2">
                      {data.ingredients.map((ing: any, i: number) => (
                        <li key={i} className="bg-white border rounded p-3 shadow-sm">
                          <p className="font-medium">
                            {ing.ingredient_name}
                            {ing.is_allergen && (
                              <span className="ml-2 px-2 py-0.5 text-xs bg-red-600 text-white rounded">Allergen</span>
                            )}
                          </p>
                          <p className="text-sm text-slate-600 mt-1">{ing.function || "Unknown Function"}</p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-slate-600 italic">No ingredients found.</p>
                  )}
                </ResultSection>

                <ResultSection title="Compliance">
                  {Array.isArray(data.compliance_analysis) && data.compliance_analysis.length > 0 ? (
                    <ul className="space-y-4">
                      {data.compliance_analysis.map((result: any, i: number) => (
                        <li
                          key={i}
                          className={`p-4 rounded border-l-4 shadow-sm ${
                            result.confidence >= 0.8
                              ? "border-green-600 bg-green-50"
                              : result.confidence >= 0.5
                              ? "border-yellow-600 bg-yellow-50"
                              : "border-red-600 bg-red-50"
                          }`}
                        >
                          <h3 className="font-bold text-lg">{result.law}</h3>
                          <p className="text-sm text-slate-700 mt-1">
                            <strong>Confidence:</strong> {(result.confidence * 100).toFixed(1)}%
                            <br />
                            <strong>Severity:</strong>{" "}
                            <span
                              className={`font-semibold ${
                                result.severity === "critical"
                                  ? "text-red-800"
                                  : result.severity === "high"
                                  ? "text-orange-700"
                                  : result.severity === "medium"
                                  ? "text-yellow-600"
                                  : "text-green-700"
                              }`}
                            >
                              {result.severity?.toUpperCase() || "UNKNOWN"}
                            </span>
                            <br />
                            <strong>Reason:</strong> {result.reason}
                          </p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-slate-600 italic">No compliance issues detected.</p>
                  )}
                </ResultSection>
              </div>
            )}
          </div>

          {/* Right Panel: File Preview */}
          <div className="lg:w-1/3">
            {file && (
              <div className="border border-slate-300 rounded-md p-4 bg-slate-50 shadow-sm">
                <h3 className="text-lg font-semibold mb-3">File Preview</h3>
                {file.type.startsWith("image/") ? (
                  <img src={URL.createObjectURL(file)} alt="Uploaded Preview" className="w-full h-auto object-contain rounded" />
                ) : file.type === "application/pdf" ? (
                  <iframe
                    src={URL.createObjectURL(file)}
                    title="PDF Preview"
                    className="w-full h-96 rounded border"
                  />
                ) : file.type === "text/plain" && textPreview !== null ? (
                  <pre className="whitespace-pre-wrap text-sm bg-white p-3 rounded max-h-96 overflow-y-auto">{textPreview}</pre>
                ) : (
                  <p className="text-slate-600 italic">Preview not available for this file type.</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}

// Reusable section wrapper
function ResultSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-2xl font-semibold mb-3 border-b border-slate-200 pb-1">{title}</h2>
      {children}
    </section>
  );
}
