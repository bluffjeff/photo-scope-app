import React, { useState } from "react";

function App() {
  const [files, setFiles] = useState([]);
  const [previewUrls, setPreviewUrls] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pdfUrl, setPdfUrl] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);

    // Generate preview thumbnails
    const previews = selectedFiles.map((file) => URL.createObjectURL(file));
    setPreviewUrls(previews);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setErrorMessage("Please select at least one file.");
      return;
    }

    setLoading(true);
    setErrorMessage("");
    setPdfUrl("");

    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      // Handle non-2xx responses
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.error || `HTTP ${res.status}`);
      }

      const data = await res.json();

      if (data.error) {
        throw new Error(data.error);
      }

      setPdfUrl(data.pdf_url);
    } catch (err) {
      console.error("❌ Upload error:", err);
      setErrorMessage(err.message || "Upload failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "700px", margin: "0 auto", padding: "20px" }}>
      <h1>📷 Photo Scope App</h1>

      <input type="file" multiple onChange={handleFileChange} />

      {/* Show previews */}
      <div style={{ display: "flex", flexWrap: "wrap", marginTop: "10px" }}>
        {previewUrls.map((url, idx) => (
          <img
            key={idx}
            src={url}
            alt={`Preview ${idx}`}
            style={{
              width: "100px",
              height: "100px",
              objectFit: "cover",
              marginRight: "10px",
              borderRadius: "5px",
              border: "1px solid #ccc",
            }}
          />
        ))}
      </div>

      <button
        onClick={handleUpload}
        disabled={loading}
        style={{
          marginTop: "15px",
          padding: "10px 20px",
          backgroundColor: "#007bff",
          color: "#fff",
          border: "none",
          borderRadius: "5px",
          cursor: loading ? "not-allowed" : "pointer",
        }}
      >
        {loading ? "Uploading..." : "Upload & Generate Report"}
      </button>

      {/* Error message */}
      {errorMessage && (
        <div style={{ marginTop: "15px", color: "red" }}>
          ❌ {errorMessage}
        </div>
      )}

      {/* PDF Download */}
      {pdfUrl && (
        <div style={{ marginTop: "20px" }}>
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "inline-block",
              padding: "10px 20px",
              backgroundColor: "green",
              color: "#fff",
              borderRadius: "5px",
              textDecoration: "none",
            }}
          >
            📄 Download Report
          </a>
        </div>
      )}
    </div>
  );
}

export default App;
