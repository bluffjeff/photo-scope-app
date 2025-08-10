import React, { useState } from "react";

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [pdfUrl, setPdfUrl] = useState("");
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  // Force backend URL so no env var issues
  const API_URL = "https://photo-scope-app-new.onrender.com";

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
    setError("");
    setPdfUrl("");
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError("Please select a file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile); // MUST be "file"

    try {
      setUploading(true);
      setError("");

      const res = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const data = await res.json();
      setPdfUrl(`${API_URL}${data.pdf_url}`);
    } catch (err) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ textAlign: "center", padding: "2rem" }}>
      <h1>📸 Photo Scope Uploader</h1>
      <input type="file" onChange={handleFileChange} />
      <br /><br />
      <button onClick={handleUpload} disabled={uploading}>
        {uploading ? "Uploading..." : "Upload & Analyze"}
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {pdfUrl && (
        <p>
          ✅ <a href={pdfUrl} target="_blank" rel="noopener noreferrer">Download PDF Report</a>
        </p>
      )}
    </div>
  );
}

export default App;
