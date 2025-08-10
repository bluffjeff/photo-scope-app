import React, { useState } from "react";

const API_URL =
  import.meta.env.VITE_API_URL ||
  (window.location.hostname.includes("render.com")
    ? "https://photo-scope-app-new.onrender.com"
    : "http://localhost:8000");

function App() {
  const [files, setFiles] = useState([]);
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
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
    <div style={{ padding: "20px", fontFamily: "Arial" }}>
      <h1>📸 Photo Scope App</h1>
      <input type="file" multiple onChange={handleFileChange} />
      <br />
      <button onClick={handleUpload} disabled={loading}>
        {loading ? "Processing..." : "Upload & Analyze"}
      </button>

      {reportData && (
        <div style={{ marginTop: "20px" }}>
          <h2>Estimate Summary</h2>
          <p>
            <strong>Total Estimate:</strong> ${reportData.total_estimate?.toFixed(2)}
          </p>
          <button onClick={() => handleDownload(reportData.job_id)}>
            Download PDF Report
          </button>

          {reportData.results.map((res, idx) => (
            <div key={idx} style={{ marginTop: "15px", padding: "10px", border: "1px solid #ccc" }}>
              <h3>{res.image}</h3>
              <p><strong>Scope:</strong> {res.scope}</p>
              <table border="1" cellPadding="5" style={{ borderCollapse: "collapse" }}>
                <thead>
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
              <p><strong>Subtotal:</strong> ${res.subtotal?.toFixed(2)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
