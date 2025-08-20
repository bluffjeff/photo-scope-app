import React, { useState } from "react";

function App() {
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [reportUrl, setReportUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const API_URL = import.meta.env.VITE_API_URL || "https://photo-scope-app-new.onrender.com";

  // Handle file selection & preview
  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);

    const previewUrls = selectedFiles.map((file) => URL.createObjectURL(file));
    setPreviews(previewUrls);
  };

  // Upload to backend
  const handleUpload = async () => {
    if (files.length === 0) {
      alert("Please select at least one image.");
      return;
    }

    setLoading(true);
    setReportUrl(null);

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    try {
      const response = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const result = await response.json();
      console.log("Upload result:", result);

      if (result.file_path) {
        setReportUrl(result.file_path);
      } else {
        alert("No report generated.");
      }
    } catch (error) {
      console.error("Error uploading:", error);
      alert("Upload failed. Check console for details.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "20px", fontFamily: "Arial" }}>
      <h2>📸 Photo Scope App</h2>
      <input type="file" multiple accept="image/*" onChange={handleFileChange} />
      
      <div style={{ marginTop: "15px", display: "flex", gap: "10px", flexWrap: "wrap" }}>
        {previews.map((src, i) => (
          <img
            key={i}
            src={src}
            alt="preview"
            width="120"
            style={{ border: "1px solid #ccc", borderRadius: "8px", padding: "4px" }}
          />
        ))}
      </div>

      <button
        onClick={handleUpload}
        disabled={loading}
        style={{ marginTop: "20px", padding: "10px 20px", cursor: "pointer" }}
      >
        {loading ? "⏳ Generating Report..." : "🚀 Upload & Generate Report"}
      </button>

      {reportUrl && (
        <div style={{ marginTop: "20px" }}>
          <a
            href={reportUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{ padding: "10px 15px", background: "#007bff", color: "#fff", borderRadius: "5px", textDecoration: "none" }}
          >
            📄 Download Report
          </a>
        </div>
      )}
    </div>
  );
}

export default App;
