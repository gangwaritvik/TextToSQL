import React, { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import DatabaseSchemaView from "./components/DatabaseSchemaView";
import ViewDataTable from "./components/ViewDataTable";
import QueryResultsPanel from "./components/QueryResultsPanel";
import QueryModal from "./components/QueryModal";
import FileUploadModal from "./components/FileUploadModal";
import "./App.css";

function App() {
  const [activeView, setActiveView] = useState("query");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isFileUploadOpen, setIsFileUploadOpen] = useState(false);
  const [queryResults, setQueryResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDatabase, setSelectedDatabase] = useState(() => {
    // Load from localStorage on mount, default to "fastapi_db"
    return localStorage.getItem("selectedDatabase") || "fastapi_db";
  });
  const [uploadRefreshTrigger, setUploadRefreshTrigger] = useState(0);

  // Save selected database to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem("selectedDatabase", selectedDatabase);
  }, [selectedDatabase]);

  const handleNewChat = async (query) => {
    try {
      setIsLoading(true);
      // Call backend API to process query
      const response = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          query: query,
          database: selectedDatabase
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const result = await response.json();
      setQueryResults([...queryResults, { ...result, database: selectedDatabase }]);
    } catch (error) {
      console.error("Error processing query:", error);
      // Show error to user
      const errorResult = {
        id: Date.now(),
        query: query,
        database: selectedDatabase,
        tables: [],
        joinPath: "",
        confidence: 0,
        sql: "ERROR",
        results: [],
        summary: `Error: ${error.message}`,
        executionTime: "0ms",
        tokensUsed: "0",
        complexity: "N/A"
      };
      setQueryResults([...queryResults, errorResult]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCloseTab = (resultId) => {
    setQueryResults(queryResults.filter(r => r.id !== resultId));
  };

  const handleClearAll = () => {
    setQueryResults([]);
  };

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handleModalSubmit = (query) => {
    handleNewChat(query);
    handleCloseModal();
  };

  const handleOpenFileUpload = () => {
    setIsFileUploadOpen(true);
  };

  const handleCloseFileUpload = () => {
    setIsFileUploadOpen(false);
  };

  const handleUploadSuccess = (result) => {
    // Trigger refresh in schema and data views
    setUploadRefreshTrigger(prev => prev + 1);
  };

  return (
    <div className="app-layout">
      <QueryModal 
        isOpen={isModalOpen} 
        onClose={handleCloseModal} 
        onSubmit={handleModalSubmit}
      />
      <FileUploadModal
        isOpen={isFileUploadOpen}
        onClose={handleCloseFileUpload}
        selectedDatabase={selectedDatabase}
        onUploadSuccess={handleUploadSuccess}
      />
      <div className="sidebar">
        <Sidebar 
          activeView={activeView} 
          onViewChange={setActiveView}
          onFileUploadClick={handleOpenFileUpload}
        />
      </div>
      <div className="main-content">
        {activeView === "query" && (
          <div className="query-layout">
            <div className="results-panel-area">
              <QueryResultsPanel 
                results={queryResults} 
                isLoading={isLoading}
                onCloseTab={handleCloseTab}
                onClearAll={handleClearAll}
                onOpenNewQuery={handleOpenModal}
                selectedDatabase={selectedDatabase}
                onDatabaseChange={setSelectedDatabase}
              />
            </div>
          </div>
        )}
        {activeView === "schema" && (
          <DatabaseSchemaView 
            refreshTrigger={uploadRefreshTrigger}
            selectedDatabase={selectedDatabase}
          />
        )}
        {activeView === "data" && (
          <ViewDataTable 
            refreshTrigger={uploadRefreshTrigger}
            selectedDatabase={selectedDatabase}
          />
        )}
      </div>
    </div>
  );
}

export default App;  
