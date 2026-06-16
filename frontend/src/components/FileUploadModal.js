import React, { useState } from "react";
import "./FileUploadModal.css";

function FileUploadModal({ isOpen, onClose, selectedDatabase, onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [error, setError] = useState(null);

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
      handleFileSelect(files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileSelect = async (file) => {
    // Validate file type
    const validTypes = ['.csv', '.xlsx', '.xls'];
    const fileExt = "." + file.name.split(".").pop().toLowerCase();

    if (!validTypes.includes(fileExt)) {
      setError(`Invalid file type. Supported: ${validTypes.join(", ")}`);
      return;
    }

    setError(null);
    setIsUploading(true);
    setUploadStatus(`Uploading ${file.name}...`);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `http://localhost:8000/upload?database=${selectedDatabase}`,
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
      setUploadStatus(
        `✅ Successfully uploaded! Table: ${result.table_name} (${result.rows} rows)`
      );

      // Call success callback to refresh database list
      setTimeout(() => {
        if (onUploadSuccess) {
          onUploadSuccess(result);
        }
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

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content file-upload-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>📤 Upload Data File</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          <p className="database-info">
            Database: <strong>{selectedDatabase}</strong>
          </p>

          <div
            className={`drop-zone ${isDragging ? "dragging" : ""} ${isUploading ? "disabled" : ""}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="drop-icon">📁</div>
            <h3>Drag & Drop your file here</h3>
            <p>or</p>
            <label className="file-input-label">
              <span className="btn-text">Browse Files</span>
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleFileInputChange}
                disabled={isUploading}
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

        <div className="modal-footer">
          <button
            className="btn btn-secondary"
            onClick={onClose}
            disabled={isUploading}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default FileUploadModal;
