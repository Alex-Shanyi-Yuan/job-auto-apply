"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  getSources, createSource, deleteSource, updateSource,
  getSuggestions, refreshSuggestions, applyForJob, dismissJob,
  getScanStatus, getJob, getGlobalFilter, updateGlobalFilter,
  JobSource, Job, ScanStatus, SourceScanResult
} from "@/lib/api";

export default function SuggestionsPage() {
  const [sources, setSources] = useState<JobSource[]>([]);
  const [suggestions, setSuggestions] = useState<Job[]>([]);
  const [newName, setNewName] = useState("");
  const [newUrl, setNewUrl] = useState("");
  const [newPrompt, setNewPrompt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // Global filter state
  const [globalFilter, setGlobalFilter] = useState("");
  const [editingGlobalFilter, setEditingGlobalFilter] = useState(false);
  const [tempGlobalFilter, setTempGlobalFilter] = useState("");
  
  // Edit mode state
  const [editingSourceId, setEditingSourceId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editUrl, setEditUrl] = useState("");
  const [editPrompt, setEditPrompt] = useState("");
  
  // Apply loading state - track multiple jobs being applied to
  const [applyingJobIds, setApplyingJobIds] = useState<Set<number>>(new Set());
  
  // Multi-select sources for scanning
  const [selectedSourceIds, setSelectedSourceIds] = useState<Set<number>>(new Set());
  
  // Scan report modal state
  const [showScanReport, setShowScanReport] = useState(false);
  const [scanReport, setScanReport] = useState<SourceScanResult[]>([]);

  const loadData = useCallback(async () => {
    try {
      const [sourcesData, suggestionsData, globalFilterData] = await Promise.all([
        getSources(),
        getSuggestions(),
        getGlobalFilter()
      ]);
      setSources(sourcesData);
      setSuggestions(suggestionsData);
      setGlobalFilter(globalFilterData);
      setError(null);
    } catch (err) {
      console.error("Failed to load data", err);
      setError("Failed to load data. Make sure the backend is running.");
    }
  }, []);

  const pollScanStatus = useCallback(async () => {
    try {
      const status = await getScanStatus();
      setScanStatus(status);
      
      // If scanning is complete, stop polling and refresh data
      if (!status.is_scanning && pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
        
        // Show scan report if there are results
        if (status.source_results && status.source_results.length > 0) {
          setScanReport(status.source_results);
          setShowScanReport(true);
        }
        
        loadData();
        setSelectedSourceIds(new Set()); // Clear selection after scan
      }
    } catch (err) {
      console.error("Failed to fetch scan status", err);
    }
  }, [loadData]);

  useEffect(() => {
    loadData();
    // Check initial scan status
    pollScanStatus();
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [loadData, pollScanStatus]);

  const handleAddSource = async () => {
    if (!newName || !newUrl) {
      setError("Please fill in name and URL");
      return;
    }
    try {
      await createSource(newName, newUrl, newPrompt || undefined);
      setNewName("");
      setNewUrl("");
      setNewPrompt("");
      setError(null);
      loadData();
    } catch (err) {
      console.error("Failed to add source", err);
      setError("Failed to add source");
    }
  };

  const handleSaveGlobalFilter = async () => {
    try {
      await updateGlobalFilter(tempGlobalFilter);
      setGlobalFilter(tempGlobalFilter);
      setEditingGlobalFilter(false);
      setError(null);
    } catch (err) {
      console.error("Failed to update global filter", err);
      setError("Failed to update global filter");
    }
  };

  const startEditingGlobalFilter = () => {
    setTempGlobalFilter(globalFilter);
    setEditingGlobalFilter(true);
  };

  const handleDeleteSource = async (id: number) => {
    try {
      await deleteSource(id);
      loadData();
    } catch (err) {
      console.error("Failed to delete source", err);
    }
  };

  const handleRefresh = async (sourceIds?: number[]) => {
    setError(null);
    try {
      await refreshSuggestions(sourceIds);
      // Start polling for status updates
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      pollIntervalRef.current = setInterval(pollScanStatus, 1500);
      pollScanStatus(); // Immediate first poll
    } catch (err: any) {
      console.error("Failed to refresh", err);
      setError(err.message || "Failed to refresh suggestions");
    }
  };

  const handleScanSelected = async () => {
    if (selectedSourceIds.size === 0) {
      setError("Please select at least one source to scan");
      return;
    }
    await handleRefresh(Array.from(selectedSourceIds));
  };

  const toggleSourceSelection = (sourceId: number) => {
    setSelectedSourceIds(prev => {
      const next = new Set(prev);
      if (next.has(sourceId)) {
        next.delete(sourceId);
      } else {
        next.add(sourceId);
      }
      return next;
    });
  };

  const toggleAllSources = () => {
    if (selectedSourceIds.size === sources.length) {
      setSelectedSourceIds(new Set());
    } else {
      setSelectedSourceIds(new Set(sources.map(s => s.id)));
    }
  };

  const handleApply = async (job: Job) => {
    // Add job to the set of applying jobs
    setApplyingJobIds(prev => new Set(prev).add(job.id));
    try {
      // Start the application process
      const appliedJob = await applyForJob(job.url);
      
      // Poll for completion - check every 2 seconds until status changes from 'processing'
      const pollForCompletion = async () => {
        const maxAttempts = 60; // 2 minutes max
        for (let i = 0; i < maxAttempts; i++) {
          await new Promise(resolve => setTimeout(resolve, 2000));
          try {
            const updatedJob = await getJob(appliedJob.id);
            if (updatedJob.status !== 'processing') {
              if (updatedJob.status === 'applied') {
                // Success - remove from suggestions
                setSuggestions(prev => prev.filter(j => j.id !== job.id));
                // Don't clear error for this job - other jobs might have errors
              } else if (updatedJob.status === 'failed') {
                // Show the actual error message from the backend
                const errorMsg = updatedJob.error_message 
                  ? `Failed to generate resume for "${job.title}": ${updatedJob.error_message}`
                  : `Failed to generate resume for "${job.title}"`;
                setError(prev => prev ? `${prev}\n${errorMsg}` : errorMsg);
              }
              return;
            }
          } catch (err) {
            console.error("Error polling job status", err);
          }
        }
        // Timeout - still processing after 2 minutes
        setError(prev => {
          const msg = `Resume generation for "${job.title}" is taking longer than expected.`;
          return prev ? `${prev}\n${msg}` : msg;
        });
      };
      
      await pollForCompletion();
    } catch (err) {
      console.error("Failed to apply", err);
      setError(prev => {
        const msg = `Failed to start application for "${job.title}"`;
        return prev ? `${prev}\n${msg}` : msg;
      });
    } finally {
      // Remove job from the set of applying jobs
      setApplyingJobIds(prev => {
        const next = new Set(prev);
        next.delete(job.id);
        return next;
      });
    }
  };

  const handleDismiss = async (id: number) => {
    try {
      await dismissJob(id);
      loadData();
    } catch (err) {
      console.error("Failed to dismiss", err);
    }
  };

  const startEditing = (source: JobSource) => {
    setEditingSourceId(source.id);
    setEditName(source.name);
    setEditUrl(source.url);
    setEditPrompt(source.filter_prompt || "");
  };

  const cancelEditing = () => {
    setEditingSourceId(null);
    setEditName("");
    setEditUrl("");
    setEditPrompt("");
  };

  const handleUpdateSource = async () => {
    if (!editingSourceId || !editName || !editUrl) {
      setError("Please fill in name and URL");
      return;
    }
    try {
      await updateSource(editingSourceId, {
        name: editName,
        url: editUrl,
        filter_prompt: editPrompt,
      });
      cancelEditing();
      setError(null);
      loadData();
    } catch (err) {
      console.error("Failed to update source", err);
      setError("Failed to update source");
    }
  };

  const getScoreBadgeStyle = (score: number | undefined) => {
    if (score === undefined) return "bg-gray-100 text-gray-600";
    if (score >= 80) return "bg-green-100 text-green-700 border-green-300";
    if (score >= 60) return "bg-yellow-100 text-yellow-700 border-yellow-300";
    if (score >= 40) return "bg-orange-100 text-orange-700 border-orange-300";
    return "bg-red-100 text-red-700 border-red-300";
  };

  const isScanning = scanStatus?.is_scanning ?? false;

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Job Suggestions</h1>
          <p className="text-gray-500 mt-1">
            Configure job sources and let AI find matching opportunities
          </p>
        </div>
        <div className="flex gap-2">
          {selectedSourceIds.size > 0 && (
            <Button 
              onClick={handleScanSelected} 
              disabled={isScanning} 
              variant="outline"
              size="lg"
            >
              {isScanning ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Scanning...
                </>
              ) : (
                <>
                  <svg className="mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  Scan Selected ({selectedSourceIds.size})
                </>
              )}
            </Button>
          )}
          <Button onClick={() => handleRefresh()} disabled={isScanning} size="lg">
            {isScanning ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Scanning...
              </>
            ) : (
              <>
                <svg className="mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Scan All
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      {/* Scan Status Panel */}
      {isScanning && scanStatus && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="pt-6">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <svg className="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <div>
                  <p className="font-semibold text-blue-900">
                    {scanStatus.current_source 
                      ? `Scanning: ${scanStatus.current_source}`
                      : scanStatus.current_step || "Initializing..."}
                  </p>
                  <p className="text-sm text-blue-700">
                    {scanStatus.current_step && scanStatus.current_source && scanStatus.current_step}
                  </p>
                </div>
              </div>
              
              {/* Progress bar */}
              <div className="w-full bg-blue-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ 
                    width: scanStatus.sources_total > 0 
                      ? `${(scanStatus.sources_completed / scanStatus.sources_total) * 100}%` 
                      : "0%" 
                  }}
                />
              </div>
              
              {/* Stats */}
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold text-blue-900">
                    {scanStatus.sources_completed}/{scanStatus.sources_total}
                  </p>
                  <p className="text-xs text-blue-700">Sources</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-blue-900">{scanStatus.jobs_found}</p>
                  <p className="text-xs text-blue-700">Jobs Found</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-blue-900">{scanStatus.jobs_scored}</p>
                  <p className="text-xs text-blue-700">Jobs Scored</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sources Section */}
      <Card>
        <CardHeader>
          <CardTitle>Job Sources</CardTitle>
          <CardDescription>
            Add job board search URLs. The AI will scan these pages and extract matching jobs.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Global Filter */}
          <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <svg className="h-5 w-5 text-purple-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                </svg>
                <Label className="font-semibold text-purple-900">Global Filter</Label>
              </div>
              {!editingGlobalFilter && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={startEditingGlobalFilter}
                  disabled={isScanning}
                >
                  <svg className="h-4 w-4 text-purple-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </Button>
              )}
            </div>
            <p className="text-xs text-purple-700 mb-2">
              This filter is applied to ALL sources. Individual source filters are combined with this.
            </p>
            {editingGlobalFilter ? (
              <div className="flex gap-2">
                <Input
                  value={tempGlobalFilter}
                  onChange={(e) => setTempGlobalFilter(e.target.value)}
                  placeholder="e.g., Remote software engineering roles, no senior positions"
                  className="flex-1"
                />
                <Button onClick={handleSaveGlobalFilter} size="sm">
                  Save
                </Button>
                <Button variant="outline" size="sm" onClick={() => setEditingGlobalFilter(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <p className="text-sm text-purple-800 bg-white/50 rounded px-3 py-2">
                {globalFilter || <span className="text-purple-400 italic">No global filter set. Click edit to add one.</span>}
              </p>
            )}
          </div>

          {/* Add Source Form */}
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="name">Source Name</Label>
              <Input 
                id="name"
                placeholder="e.g., LinkedIn Python Jobs" 
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="url">Search Results URL</Label>
              <Input 
                id="url"
                placeholder="https://linkedin.com/jobs/search?..." 
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="prompt">Source-Specific Filter <span className="text-gray-400">(optional)</span></Label>
              <Input 
                id="prompt"
                placeholder="Additional filter for this source" 
                value={newPrompt}
                onChange={(e) => setNewPrompt(e.target.value)}
              />
            </div>
            <div className="flex items-end">
              <Button onClick={handleAddSource} className="w-full">
                <svg className="mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Add Source
              </Button>
            </div>
          </div>

          {/* Sources List */}
          <div className="space-y-2">
            {/* Select All Header */}
            {sources.length > 0 && (
              <div className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600">
                <input
                  type="checkbox"
                  checked={sources.length > 0 && selectedSourceIds.size === sources.length}
                  onChange={toggleAllSources}
                  disabled={isScanning}
                  className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 disabled:opacity-50"
                />
                <span>
                  {selectedSourceIds.size === sources.length 
                    ? "Deselect All" 
                    : `Select All (${sources.length})`}
                </span>
              </div>
            )}
            {sources.map((source) => {
              const isCurrentlyScanning = isScanning && scanStatus?.current_source === source.name;
              const isEditing = editingSourceId === source.id;
              
              if (isEditing) {
                return (
                  <div 
                    key={source.id} 
                    className="p-4 rounded-lg border bg-amber-50 border-amber-200"
                  >
                    <div className="grid gap-4 md:grid-cols-4">
                      <div className="space-y-2">
                        <Label htmlFor={`edit-name-${source.id}`}>Source Name</Label>
                        <Input 
                          id={`edit-name-${source.id}`}
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor={`edit-url-${source.id}`}>Search Results URL</Label>
                        <Input 
                          id={`edit-url-${source.id}`}
                          value={editUrl}
                          onChange={(e) => setEditUrl(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor={`edit-prompt-${source.id}`}>Source-Specific Filter <span className="text-gray-400">(optional)</span></Label>
                        <Input 
                          id={`edit-prompt-${source.id}`}
                          value={editPrompt}
                          onChange={(e) => setEditPrompt(e.target.value)}
                          placeholder="Leave empty to use global filter only"
                        />
                      </div>
                      <div className="flex items-end gap-2">
                        <Button onClick={handleUpdateSource} className="flex-1">
                          <svg className="mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Save
                        </Button>
                        <Button variant="outline" onClick={cancelEditing}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              }
              
              return (
                <div 
                  key={source.id} 
                  className={`flex justify-between items-center p-4 rounded-lg border transition-colors ${
                    isCurrentlyScanning 
                      ? "bg-blue-50 border-blue-300 ring-2 ring-blue-200" 
                      : selectedSourceIds.has(source.id)
                      ? "bg-indigo-50 border-indigo-300"
                      : "bg-slate-50"
                  }`}
                >
                  <div className="flex items-center gap-3 flex-1 mr-4 min-w-0">
                    {/* Checkbox for selection */}
                    <input
                      type="checkbox"
                      checked={selectedSourceIds.has(source.id)}
                      onChange={() => toggleSourceSelection(source.id)}
                      disabled={isScanning}
                      className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 disabled:opacity-50"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium flex items-center gap-2">
                        {source.name}
                        {isCurrentlyScanning && (
                          <Badge variant="default" className="bg-blue-600 animate-pulse">
                            Scanning...
                          </Badge>
                        )}
                      </div>
                      <div className="text-sm text-gray-500 truncate">{source.url}</div>
                      <div className="text-sm text-gray-400 mt-1">
                        {source.filter_prompt ? (
                          <span>Additional filter: <span className="text-gray-600">{source.filter_prompt}</span></span>
                        ) : (
                          <span className="italic">Using global filter only</span>
                        )}
                        {source.last_scraped_at && (
                          <span className="ml-4">
                            Last scan: {new Date(source.last_scraped_at).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => startEditing(source)} 
                      disabled={isScanning}
                      title="Edit source"
                    >
                      <svg className="h-4 w-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => handleDeleteSource(source.id)} 
                      disabled={isScanning}
                      title="Delete source"
                    >
                      <svg className="h-4 w-4 text-red-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </Button>
                  </div>
                </div>
              );
            })}
            {sources.length === 0 && (
              <div className="text-center text-gray-500 py-8">
                No sources configured. Add a job board search URL above to get started.
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Suggestions Section */}
      <div>
        <h2 className="text-xl font-semibold mb-4">
          Suggested Jobs ({suggestions.length})
        </h2>
        
        {suggestions.length === 0 ? (
          <div className="text-center py-12 text-gray-500 bg-slate-50 rounded-lg border">
            <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <p>No suggestions found yet.</p>
            <p className="text-sm mt-1">Add sources above and click &quot;Scan for Jobs&quot; to discover opportunities.</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {suggestions.map((job) => (
              <Card key={job.id} className="flex flex-col">
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-start gap-2">
                    <CardTitle className="text-lg font-semibold line-clamp-2" title={job.title}>
                      {job.title}
                    </CardTitle>
                    {job.score !== undefined && (
                      <Badge className={`shrink-0 ${getScoreBadgeStyle(job.score)}`}>
                        {job.score}%
                      </Badge>
                    )}
                  </div>
                  <CardDescription className="flex justify-between items-center">
                    <span>{job.company}</span>
                    <span className="text-xs text-gray-400">
                      {new Date(job.created_at).toLocaleDateString()}
                    </span>
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col justify-end">
                  <div className="flex justify-between items-center mt-4 gap-2">
                    <a 
                      href={job.url} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="text-sm text-blue-600 hover:underline flex items-center"
                    >
                      View Job
                      <svg className="ml-1 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={() => handleDismiss(job.id)} disabled={applyingJobIds.has(job.id)}>
                        Dismiss
                      </Button>
                      <Button size="sm" onClick={() => handleApply(job)} disabled={applyingJobIds.has(job.id)}>
                        {applyingJobIds.has(job.id) ? (
                          <>
                            <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Applying...
                          </>
                        ) : (
                          "Apply"
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Scan Report Modal */}
      {showScanReport && scanReport && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[85vh] flex flex-col">
            <div className="p-6 border-b">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">Scan Report</h2>
                <Button variant="ghost" size="sm" onClick={() => setShowScanReport(false)}>
                  <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </Button>
              </div>
              <p className="text-sm text-gray-500 mt-1">Summary of the last scan operation</p>
            </div>
            <div className="flex-1 overflow-auto p-6">
              {scanReport.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  No sources were scanned.
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Summary Stats */}
                  <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="bg-blue-50 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-blue-700">
                        {scanReport.reduce((sum, r) => sum + r.jobs_found, 0)}
                      </div>
                      <div className="text-sm text-blue-600">Jobs Found</div>
                    </div>
                    <div className="bg-green-50 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-green-700">
                        {scanReport.reduce((sum, r) => sum + r.jobs_added, 0)}
                      </div>
                      <div className="text-sm text-green-600">New Jobs Added</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-gray-700">
                        {scanReport.reduce((sum, r) => sum + r.jobs_skipped, 0)}
                      </div>
                      <div className="text-sm text-gray-600">Already Existed</div>
                    </div>
                  </div>

                  {/* Per-Source Results */}
                  <div className="space-y-4">
                    <h3 className="font-medium text-gray-700">Per-Source Results</h3>
                    {scanReport.map((result, index) => (
                      <div 
                        key={index} 
                        className={`rounded-lg border ${
                          result.error 
                            ? "bg-red-50 border-red-200" 
                            : result.jobs_added > 0 
                            ? "bg-green-50 border-green-200"
                            : "bg-gray-50 border-gray-200"
                        }`}
                      >
                        {/* Source Header */}
                        <div className="p-4 border-b border-inherit">
                          <div className="flex items-center justify-between">
                            <div className="font-medium">{result.source_name}</div>
                            <div className="flex items-center gap-2">
                              {result.error ? (
                                <Badge variant="destructive">Error</Badge>
                              ) : result.jobs_added > 0 ? (
                                <Badge className="bg-green-600">+{result.jobs_added} new</Badge>
                              ) : (
                                <Badge variant="secondary">No new jobs</Badge>
                              )}
                              <a 
                                href={result.source_url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-800"
                                title="Open source URL"
                              >
                                <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                              </a>
                            </div>
                          </div>
                          {result.error ? (
                            <div className="text-sm text-red-600 mt-2">{result.error}</div>
                          ) : (
                            <div className="text-sm text-gray-500 mt-2 flex gap-4">
                              <span>Found: {result.jobs_found}</span>
                              <span>Added: {result.jobs_added}</span>
                              <span>Skipped: {result.jobs_skipped}</span>
                            </div>
                          )}
                        </div>

                        {/* Job Lists */}
                        {!result.error && (result.added_jobs?.length > 0 || result.skipped_jobs?.length > 0) && (
                          <div className="p-4 space-y-4">
                            {/* Added Jobs */}
                            {result.added_jobs?.length > 0 && (
                              <div>
                                <div className="text-sm font-medium text-green-700 mb-2 flex items-center gap-1">
                                  <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                  </svg>
                                  New Jobs Added ({result.added_jobs.length})
                                </div>
                                <div className="space-y-1 max-h-32 overflow-y-auto">
                                  {result.added_jobs.map((job, jobIndex) => (
                                    <div key={jobIndex} className="flex items-center justify-between text-sm bg-white/50 rounded px-2 py-1">
                                      <div className="flex items-center gap-2 min-w-0 flex-1">
                                        <span className="truncate" title={job.title}>{job.title}</span>
                                        <span className="text-gray-400 text-xs shrink-0">@ {job.company}</span>
                                        {job.score !== null && (
                                          <Badge 
                                            variant="outline" 
                                            className={`text-xs shrink-0 ${
                                              job.score >= 70 ? "border-green-500 text-green-700" :
                                              job.score >= 50 ? "border-yellow-500 text-yellow-700" :
                                              job.score >= 30 ? "border-orange-500 text-orange-700" :
                                              "border-red-500 text-red-700"
                                            }`}
                                          >
                                            {job.score}
                                          </Badge>
                                        )}
                                      </div>
                                      <a 
                                        href={job.url} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:text-blue-800 shrink-0 ml-2"
                                        title="View job posting"
                                      >
                                        <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                        </svg>
                                      </a>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Skipped Jobs */}
                            {result.skipped_jobs?.length > 0 && (
                              <div>
                                <div className="text-sm font-medium text-gray-500 mb-2 flex items-center gap-1">
                                  <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                  Already Existed ({result.skipped_jobs.length})
                                </div>
                                <div className="space-y-1 max-h-24 overflow-y-auto">
                                  {result.skipped_jobs.map((job, jobIndex) => (
                                    <div key={jobIndex} className="flex items-center justify-between text-sm bg-white/30 rounded px-2 py-1 text-gray-600">
                                      <div className="flex items-center gap-2 min-w-0 flex-1">
                                        <span className="truncate" title={job.title}>{job.title}</span>
                                        <span className="text-gray-400 text-xs shrink-0">@ {job.company}</span>
                                        {job.score !== null && (
                                          <Badge 
                                            variant="outline" 
                                            className={`text-xs shrink-0 ${
                                              job.score >= 70 ? "border-green-500 text-green-700" :
                                              job.score >= 50 ? "border-yellow-500 text-yellow-700" :
                                              job.score >= 30 ? "border-orange-500 text-orange-700" :
                                              "border-red-500 text-red-700"
                                            }`}
                                          >
                                            {job.score}
                                          </Badge>
                                        )}
                                      </div>
                                      <a 
                                        href={job.url} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:text-blue-800 shrink-0 ml-2"
                                        title="View job posting"
                                      >
                                        <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                        </svg>
                                      </a>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="p-4 border-t bg-gray-50 rounded-b-lg">
              <Button onClick={() => setShowScanReport(false)} className="w-full">
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
