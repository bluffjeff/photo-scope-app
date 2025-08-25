import React, { useState } from "react";

function App() {
  const [phase, setPhase] = useState("inspection");
  const [files, setFiles] = useState([]);
  const [notes, setNotes] = useState("");
  const [scope, setScope] = useState("");
  const [sketch, setSketch] = useState(null);
  const [jobId, setJobId] = useState("");
  const [reportUrl, setReportUrl] = useState("");

  const backendUrl = import.meta.env.VITE_API_URL || "https://photo-scope-app-new.onrender.com";

  const handleFileChange = (e) => {
    setFiles([...e.target.files]);
  };

  const handleSketchChange = (e) => {
    setSketch(e.target.files[0]);
  };

  const uploadInspection = async () => {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    formData.append("notes", notes);
    formData.append("scope", scope);
    if (sketch) formData.append("sketch", sketch);

    try {
      const res = await fetch(`${backendUrl}/upload-inspection`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setJobId(data.job_id);
      alert("✅ Inspection uploaded successfully. Save Job ID: " + data.job_id);
    } catch (err) {
      console.error(err);
      alert("❌ Failed to upload inspection");
    }
  };

  const uploadWork = async () => {
    if (!jobId) {
      alert("❌ Please upload inspection first to get a Job ID.");
      return;
    }
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    try {
      const res = await fetch(`${backendUrl}/upload-work/${jobId}`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      alert("✅ Work photos uploaded for Job ID: " + data.job_id);
    } catch (err) {
      console.error(err);
      alert("❌ Failed to upload work photos");
    }
  };

  const generateReport = async () => {
    if (!jobId) {
      alert("❌ No Job ID found.");
      return;
    }
    try {
      const res = await fetch(`${backendUrl}/generate-report/${jobId}`);
      const data = await res.json();
      if (data.report_url) {
        setReportUrl(`${backendUrl}${data.report_url}`);
      } else {
        alert("❌ Report generation failed");
      }
    } catch (err) {
      console.error(err);
      alert("❌ Error generating report");
    }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">📸 Photo Scope App</h1>

      <div className="mb-4">
        <label className="mr-4">
          <input
            type="radio"
            value="inspection"
            checked={phase === "inspection"}
            onChange={() => setPhase("inspection")}
          />{" "}
          Inspection Phase
        </label>
        <label>
          <input
            type="radio"
            value="work"
            checked={phase === "work"}
            onChange={() => setPhase("work")}
          />{" "}
          Work Completed Phase
        </label>
      </div>

      {phase === "inspection" && (
        <>
          <textarea
            className="w-full border p-2 mb-2"
            placeholder="Enter inspector notes..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <textarea
            className="w-full border p-2 mb-2"
            placeholder="Enter scope..."
            value={scope}
            onChange={(e) => setScope(e.target.value)}
          />
          <div className="mb-2">
            <label>Upload Sketch: </label>
            <input type="file" accept=".jpg,.jpeg,.png,.pdf" onChange={handleSketchChange} />
          </div>
        </>
      )}

      <div className="mb-4">
        <label>Upload Photos: </label>
        <input type="file" multiple accept="image/*" onChange={handleFileChange} />
      </div>

      {phase === "inspection" ? (
        <button className="bg-blue-500 text-white px-4 py-2 rounded" onClick={uploadInspection}>
          Upload Inspection
        </button>
      ) : (
        <button className="bg-green-500 text-white px-4 py-2 rounded" onClick={uploadWork}>
          Upload Work Photos
        </button>
      )}

      <div className="mt-4">
        <button className="bg-purple-500 text-white px-4 py-2 rounded" onClick={generateReport}>
          Generate Final Report
        </button>
      </div>

      {reportUrl && (
        <div className="mt-4">
          <a
            href={reportUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 underline"
          >
            📄 Download Report
          </a>
        </div>
      )}
    </div>
  );
}

export default App;
