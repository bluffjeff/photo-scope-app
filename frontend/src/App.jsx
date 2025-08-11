import React, { useState } from "react";

function App() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [pdfUrl, setPdfUrl] = useState("");
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  const API_URL = "https://photo-scope-app-new.onrender.com"; // your backend URL

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    setSelectedFiles(files);
    setPreviews(files.map((file) => URL.createObjectURL(file)));
    setError("");
    setPdfUrl("");
  };

  const handleUpload = async () => {
    if (!selectedFiles.length) {
      setError("Please select at least one file.");
      return;
    }

    const formData = new FormData();
    // Must be exactly "files" to match backend parameter
    selectedFiles.forEach((file) => {
      formData.append("files", file);
    });

    try {
      setUploading(true);
      const res = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error(await res.text());
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
      <input type="file" multiple onChange={handleFileChange} />
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "10px",
          marginTop: "1rem",
          justifyContent: "center",
        }}
      >
        {previews.map((src, idx) => (
          <img
            key={idx}
            src={src}
            alt={`Preview ${idx}`}
            style={{ width: "150px", border: "1px solid #ccc" }}
          />
        ))}
      </div>
      <br />
      <button onClick={handleUpload} disabled={uploading}>
        {uploading ? "Uploading..." : "Upload & Analyze"}
      </button>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {pdfUrl && (
        <p>
          ✅{" "}
          <a href={pdfUrl} target="_blank" rel="noopener noreferrer">
            Download PDF Report
          </a>
        </p>
      )}
    </div>
  );
}

export default App;
