import React, { useState, useEffect } from "react";
import "./FileUploadModal.css";

function FileUploadModal({ isOpen, onClose, selectedDatabase, onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [error, setError] = useState(null);
  const [uploadMode, setUploadMode] = useState("current"); // "current" | "new"
  const [newDbName, setNewDbName] = useState("");

  // Reset transient state whenever the modal is closed so reopening starts fresh
  // (otherwise a previous "uploaded successfully" message lingers).
  useEffect(() => {
    if (!isOpen) {
      setIsDragging(false);
      setIsUploading(false);
      setUploadStatus(null);
      setError(null);
      setUploadMode("current");
      setNewDbName("");
    }
  }, [isOpen]);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFilesSelect(Array.from(files));
    }
  };

  const handleFileInputChange = (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      handleFilesSelect(Array.from(files));
    }
  };

  const handleFilesSelect = async (files) => {
    // Validate file types up front; reject the whole batch if any is unsupported
    const validTypes = ['.csv', '.xlsx', '.xls'];
    const invalid = files.filter(
      (f) => !validTypes.includes("." + f.name.split(".").pop().toLowerCase())
    );

    if (invalid.length > 0) {
      setError(
        `Invalid file type: ${invalid.map((f) => f.name).join(", ")}. ` +
          `Supported: ${validTypes.join(", ")}`
      );
      return;
    }

    // When creating a new database, a name is required
    if (uploadMode === "new" && !newDbName.trim()) {
      setError("Please enter a name for the new database.");
      return;
    }

    setError(null);
    setIsUploading(true);

    try {
      let targetDatabase = selectedDatabase;

      // Create the new database first if requested
      if (uploadMode === "new") {
        setUploadStatus(`Creating database "${newDbName.trim()}"...`);
        const createResponse = await fetch("http://localhost:8000/databases", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: newDbName.trim() }),
        });

        if (!createResponse.ok) {
          const errorData = await createResponse.json();
          throw new Error(errorData.detail || "Failed to create database");
        }

        const createResult = await createResponse.json();
        targetDatabase = createResult.database;
      }

      const fileLabel =
        files.length === 1 ? files[0].name : `${files.length} files`;
      setUploadStatus(`Uploading ${fileLabel} to ${targetDatabase}...`);

      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));

      const response = await fetch(
        `http://localhost:8000/upload?database=${targetDatabase}`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Upload failed");
      }

      const result = await response.json();
      const uploaded = result.uploaded || [];
      const failed = result.failed || [];

      let statusMsg = `Uploaded ${uploaded.length} of ${result.total} file${
        result.total === 1 ? "" : "s"
      } to ${targetDatabase}.`;
      if (failed.length > 0) {
        statusMsg +=
          ` Failed: ` + failed.map((f) => `${f.filename} (${f.error})`).join("; ");
      }
      setUploadStatus(statusMsg);

      // Call success callback (include the database we uploaded into so the
      // app can switch to it and refresh the database list)
      setTimeout(() => {
        if (onUploadSuccess) {
          onUploadSuccess({ ...result, database: targetDatabase });
        }
        setNewDbName("");
        setUploadMode("current");
        onClose();
      }, 2000);
    } catch (err) {
      setError(err.message || "Upload failed");
      setUploadStatus(null);
    } finally {
      setIsUploading(false);
    }
  };

  if (!isOpen) return null;

  const fileSelectionDisabled =
    isUploading || (uploadMode === "new" && !newDbName.trim());

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content file-upload-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>📤 Upload Data File</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          <div className="upload-destination">
            <p className="destination-title">Where should this file go?</p>

            <label className={`destination-option ${uploadMode === "current" ? "active" : ""}`}>
              <input
                type="radio"
                name="uploadMode"
                value="current"
                checked={uploadMode === "current"}
                onChange={() => setUploadMode("current")}
                disabled={isUploading}
              />
              <span className="option-text">
                Upload to current database <strong>{selectedDatabase}</strong>
              </span>
            </label>

            <label className={`destination-option ${uploadMode === "new" ? "active" : ""}`}>
              <input
                type="radio"
                name="uploadMode"
                value="new"
                checked={uploadMode === "new"}
                onChange={() => setUploadMode("new")}
                disabled={isUploading}
              />
              <span className="option-text">Create a new database</span>
            </label>

            {uploadMode === "new" && (
              <input
                type="text"
                className="new-db-input"
                placeholder="Enter new database name"
                value={newDbName}
                onChange={(e) => setNewDbName(e.target.value)}
                disabled={isUploading}
              />
            )}
          </div>

          <div
            className={`drop-zone ${isDragging ? "dragging" : ""} ${fileSelectionDisabled ? "disabled" : ""}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="drop-icon">📁</div>
            <h3>Drag & Drop your files here</h3>
            <p>or</p>
            <label className="file-input-label">
              <span className="btn-text">Browse Files</span>
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                multiple
                onChange={handleFileInputChange}
                disabled={fileSelectionDisabled}
                style={{ display: "none" }}
              />
            </label>
          </div>

          <div className="file-info">
            <p className="info-title">Supported formats:</p>
            <ul>
              <li><strong>.CSV</strong> - Comma-separated values</li>
              <li><strong>.XLSX</strong> - Excel workbook</li>
              <li><strong>.XLS</strong> - Excel 97-2003</li>
            </ul>
          </div>

          {uploadStatus && (
            <div className="upload-status success">
              ✅ {uploadStatus}
            </div>
          )}

          {error && (
            <div className="upload-status error">
              ❌ {error}
            </div>
          )}

          {isUploading && (
            <div className="upload-progress">
              <div className="spinner"></div>
              <p>Uploading...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default FileUploadModal;
