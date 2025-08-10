import React, { useState } from "react";

const API_URL =
  import.meta.env.VITE_API_URL ||
  (window.location.hostname.includes("render.com")
    ? "https://photo-scope-app-new.onrender.com"
    : "http://localhost:8000");

function App() {
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);
    setPreviews(selectedFiles.map((file) => URL.createObjectURL(file)));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      alert("Please select at least one file.");
      return;
    }

    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");

      const data = await res.json();
      setReportData(data);
    } catch (error) {
      console.error("Error uploading files:", error);
      alert("Error uploading files");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (jobId) => {
    try {
      const res = await fetch(`${API_URL}/download/${jobId}`);
      if (!res.ok) throw new Error("Download failed");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${jobId}_scope_report.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (error) {
      console.error("Error downloading report:", error);
      alert("Error downloading report");
    }
  };

  return (
    <div style={{ fontFamily: "Arial, sans-serif", backgroundColor: "#f4f6f8", minHeight: "100vh", padding: "20px" }}>
      <div style={{ maxWidth: "900px", margin: "0 auto", background: "#fff", borderRadius: "10px", padding: "30px", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}>
        
        {/* HEADER */}
        <header style={{ textAlign: "center", marginBottom: "30px" }}>
          <h1 style={{ color: "#1a73e8", fontSize: "2rem", marginBottom: "10px" }}>📸 Photo Scope App</h1>
          <p style={{ color: "#555" }}>Upload property damage photos and get a detailed scope of work & Xactimate line items with Bay Area pricing.</p>
        </header>

        {/* FILE UPLOAD */}
        <div style={{ marginBottom: "20px", textAlign: "center" }}>
          <input
            type="file"
            multiple
            onChange={handleFileChange}
            style={{
              border: "1px solid #ccc",
              padding: "10px",
              borderRadius: "6px",
              background: "#f9f9f9",
            }}
          />
          <br />
          <button
            onClick={handleUpload}
            disabled={loading}
            style={{
              marginTop: "15px",
              backgroundColor: "#1a73e8",
              color: "#fff",
              border: "none",
              padding: "10px 20px",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "1rem",
            }}
          >
            {loading ? "Processing..." : "Upload & Analyze"}
          </button>
        </div>

        {/* Thumbnails before upload */}
        {previews.length > 0 && !reportData && (
          <div style={{ display: "flex", gap: "10px", marginTop: "10px", flexWrap: "wrap", justifyContent: "center" }}>
            {previews.map((src, idx) => (
              <img
                key={idx}
                src={src}
                alt={`preview-${idx}`}
                style={{
                  width: "100px",
                  height: "100px",
                  objectFit: "cover",
                  borderRadius: "6px",
                  border: "1px solid #ccc",
                }}
              />
            ))}
          </div>
        )}

        {/* REPORT RESULTS */}
        {reportData && (
          <div style={{ marginTop: "30px" }}>
            <h2 style={{ color: "#1a73e8" }}>Estimate Summary</h2>
            <p><strong>Total Estimate:</strong> ${reportData.total_estimate?.toFixed(2)}</p>
            <button
              onClick={() => handleDownload(reportData.job_id)}
              style={{
                backgroundColor: "#34a853",
                color: "#fff",
                border: "none",
                padding: "8px 15px",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              Download PDF Report
            </button>

            {reportData.results.map((res, idx) => (
              <div key={idx} style={{ marginTop: "20px", padding: "15px", border: "1px solid #ddd", borderRadius: "8px", background: "#fafafa" }}>
                {/* Thumbnail for each result */}
                {previews[idx] && (
                  <img
                    src={previews[idx]}
                    alt={res.image}
                    style={{ width: "120px", borderRadius: "6px", marginBottom: "10px" }}
                  />
                )}
                <h3 style={{ marginBottom: "10px" }}>{res.image}</h3>
                <p><strong>Scope:</strong> {res.scope}</p>
                <table border="1" cellPadding="5" style={{ borderCollapse: "collapse", width: "100%", marginTop: "10px" }}>
                  <thead style={{ background: "#e9ecef" }}>
                    <tr>
                      <th>Code</th>
                      <th>Description</th>
                      <th>Qty</th>
                      <th>Unit Price</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {res.line_items.map((item, i) => (
                      <tr key={i}>
                        <td>{item.code}</td>
                        <td>{item.desc}</td>
                        <td>{item.qty}</td>
                        <td>${item.price}</td>
                        <td>${item.total}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p style={{ marginTop: "10px" }}><strong>Subtotal:</strong> ${res.subtotal?.toFixed(2)}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
