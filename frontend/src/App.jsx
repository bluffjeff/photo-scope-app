import React, { useState } from 'react';

function App() {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [filePreviews, setFilePreviews] = useState([]);
  const [downloadLink, setDownloadLink] = useState(null);
  const [results, setResults] = useState([]);

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    setSelectedFiles(files);

    // Create preview URLs
    const previews = files.map(file => URL.createObjectURL(file));
    setFilePreviews(previews);
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      alert("Please select files first");
      return;
    }

    const formData = new FormData();
    for (let i = 0; i < selectedFiles.length; i++) {
      formData.append("files", selectedFiles[i]);
    }

    try {
      const res = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      console.log(data);

      if (data.job_id) {
        setDownloadLink(`http://localhost:8000/download/${data.job_id}`);
        setResults(data.results || []);
      }
    } catch (err) {
      console.error("Upload failed", err);
    }
  };

  return (
    <div style={{ padding: "20px", fontFamily: "Arial, sans-serif" }}>
      <h1>📸 Photo Scope Uploader</h1>
      <input type="file" multiple onChange={handleFileChange} />
      <button
        onClick={handleUpload}
        style={{
          marginLeft: "10px",
          padding: "8px 12px",
          background: "#007bff",
          color: "white",
          border: "none",
          borderRadius: "5px",
          cursor: "pointer"
        }}
      >
        Upload
      </button>

      {downloadLink && (
        <div style={{ marginTop: "20px" }}>
          <a
            href={downloadLink}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              background: "green",
              color: "white",
              padding: "10px 15px",
              textDecoration: "none",
              borderRadius: "5px"
            }}
          >
            📄 Download Scope Report
          </a>
        </div>
      )}

      {results.length > 0 && (
        <div style={{ marginTop: "30px" }}>
          <h2>Scope & Line Items Preview</h2>
          {results.map((res, idx) => (
            <div
              key={idx}
              style={{
                border: "1px solid #ccc",
                padding: "15px",
                marginBottom: "15px",
                borderRadius: "8px",
                display: "flex",
                gap: "15px"
              }}
            >
              {/* Thumbnail preview */}
              {filePreviews[idx] && (
                <img
                  src={filePreviews[idx]}
                  alt={res.image}
                  style={{
                    width: "150px",
                    height: "150px",
                    objectFit: "cover",
                    borderRadius: "8px",
                    border: "1px solid #ddd"
                  }}
                />
              )}

              {/* Scope & line items */}
              <div style={{ flex: 1 }}>
                <h3>{res.image}</h3>
                <p><strong>Scope:</strong> {res.scope}</p>
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    marginTop: "10px"
                  }}
                >
                  <thead>
                    <tr>
                      <th style={{ border: "1px solid #ddd", padding: "8px" }}>Code</th>
                      <th style={{ border: "1px solid #ddd", padding: "8px" }}>Description</th>
                      <th style={{ border: "1px solid #ddd", padding: "8px" }}>Qty</th>
                      <th style={{ border: "1px solid #ddd", padding: "8px" }}>Unit Price</th>
                      <th style={{ border: "1px solid #ddd", padding: "8px" }}>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {res.line_items.map((item, i) => (
                      <tr key={i}>
                        <td style={{ border: "1px solid #ddd", padding: "8px" }}>{item.code}</td>
                        <td style={{ border: "1px solid #ddd", padding: "8px" }}>{item.desc}</td>
                        <td style={{ border: "1px solid #ddd", padding: "8px" }}>{item.qty}</td>
                        <td style={{ border: "1px solid #ddd", padding: "8px" }}>${item.price}</td>
                        <td style={{ border: "1px solid #ddd", padding: "8px" }}>${item.total}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p style={{ marginTop: "10px" }}><strong>Subtotal:</strong> ${res.subtotal}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
