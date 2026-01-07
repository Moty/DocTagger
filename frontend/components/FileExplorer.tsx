"use client";

import { useState, useMemo } from "react";
import type { ProcessedFile } from "@/lib/types";

interface FileExplorerProps {
  files: ProcessedFile[];
  title?: string;
}

type ViewMode = "list" | "grid" | "details";
type GroupBy = "none" | "document_type" | "status" | "date";
type SortBy = "name" | "type" | "status" | "date";
type SortOrder = "asc" | "desc";

// File type icons mapping
const getFileIcon = (type?: string) => {
  const iconMap: Record<string, { icon: string; color: string }> = {
    invoice: { icon: "📄", color: "bg-blue-100 text-blue-700" },
    bill: { icon: "💰", color: "bg-green-100 text-green-700" },
    receipt: { icon: "🧾", color: "bg-yellow-100 text-yellow-700" },
    contract: { icon: "📝", color: "bg-purple-100 text-purple-700" },
    letter: { icon: "✉️", color: "bg-pink-100 text-pink-700" },
    report: { icon: "📊", color: "bg-indigo-100 text-indigo-700" },
    statement: { icon: "📋", color: "bg-cyan-100 text-cyan-700" },
    insurance: { icon: "🛡️", color: "bg-orange-100 text-orange-700" },
    tax: { icon: "🏛️", color: "bg-red-100 text-red-700" },
    medical: { icon: "🏥", color: "bg-teal-100 text-teal-700" },
    legal: { icon: "⚖️", color: "bg-amber-100 text-amber-700" },
    other: { icon: "📁", color: "bg-gray-100 text-gray-700" },
  };
  
  const normalizedType = type?.toLowerCase() || "other";
  for (const [key, value] of Object.entries(iconMap)) {
    if (normalizedType.includes(key)) {
      return value;
    }
  }
  return iconMap.other;
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case "success":
      return { icon: "✓", color: "text-green-600 bg-green-100" };
    case "failed":
      return { icon: "✗", color: "text-red-600 bg-red-100" };
    case "skipped":
      return { icon: "⏭", color: "text-yellow-600 bg-yellow-100" };
    default:
      return { icon: "?", color: "text-gray-600 bg-gray-100" };
  }
};

export function FileExplorer({ files, title = "Processed Files" }: FileExplorerProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("details");
  const [groupBy, setGroupBy] = useState<GroupBy>("none");
  const [sortBy, setSortBy] = useState<SortBy>("name");
  const [sortOrder, setSortOrder] = useState<SortOrder>("asc");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [selectedFile, setSelectedFile] = useState<ProcessedFile | null>(null);

  // Extract all unique tags from files
  const allTags = useMemo(() => {
    const tags = new Set<string>();
    files.forEach((file) => {
      file.result?.tags?.forEach((tag) => tags.add(tag));
    });
    return Array.from(tags).sort();
  }, [files]);



  // Filter and sort files
  const processedFiles = useMemo(() => {
    let result = [...files];

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (file) =>
          file.name.toLowerCase().includes(query) ||
          file.result?.title?.toLowerCase().includes(query) ||
          file.result?.document_type?.toLowerCase().includes(query) ||
          file.result?.tags?.some((tag) => tag.toLowerCase().includes(query))
      );
    }

    // Apply tag filter
    if (selectedTags.length > 0) {
      result = result.filter((file) =>
        selectedTags.every((tag) => file.result?.tags?.includes(tag))
      );
    }

    // Sort files
    result.sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case "name":
          comparison = a.name.localeCompare(b.name);
          break;
        case "type":
          comparison = (a.result?.document_type || "").localeCompare(
            b.result?.document_type || ""
          );
          break;
        case "status":
          comparison = a.status.localeCompare(b.status);
          break;
        case "date":
          // If we have dates in the future, sort by them
          comparison = a.name.localeCompare(b.name);
          break;
      }
      return sortOrder === "asc" ? comparison : -comparison;
    });

    return result;
  }, [files, searchQuery, selectedTags, sortBy, sortOrder]);

  // Group files
  const groupedFiles = useMemo(() => {
    if (groupBy === "none") {
      return { "All Files": processedFiles };
    }

    const groups: Record<string, ProcessedFile[]> = {};

    processedFiles.forEach((file) => {
      let groupKey: string;
      switch (groupBy) {
        case "document_type":
          groupKey = file.result?.document_type || "Unknown";
          break;
        case "status":
          groupKey = file.status.charAt(0).toUpperCase() + file.status.slice(1);
          break;
        case "date":
          // Use the document date extracted by LLM if available
          if (file.result?.date) {
            // Format: YYYY-MM-DD -> display as Month YYYY or just the date
            const dateParts = file.result.date.split("-");
            if (dateParts.length === 3) {
              const [year, month] = dateParts;
              const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
              const monthIdx = parseInt(month, 10) - 1;
              groupKey = `${monthNames[monthIdx] || month} ${year}`;
            } else {
              groupKey = file.result.date;
            }
          } else {
            groupKey = "No Date";
          }
          break;
        default:
          groupKey = "All";
      }

      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(file);
    });

    return groups;
  }, [processedFiles, groupBy]);

  const toggleGroup = (groupName: string) => {
    const newCollapsed = new Set(collapsedGroups);
    if (newCollapsed.has(groupName)) {
      newCollapsed.delete(groupName);
    } else {
      newCollapsed.add(groupName);
    }
    setCollapsedGroups(newCollapsed);
  };

  // Check if a group is expanded (not in the collapsed set)
  const isGroupExpanded = (groupName: string) => !collapsedGroups.has(groupName);

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const handleSort = (column: SortBy) => {
    if (sortBy === column) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(column);
      setSortOrder("asc");
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      {/* Header / Toolbar */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-800">{title}</h2>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">
              {processedFiles.length} file{processedFiles.length !== 1 ? "s" : ""}
            </span>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-4">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="Search files, tags, types..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <svg
              className="absolute left-3 top-2.5 w-5 h-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>

          {/* Group By */}
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Group:</label>
            <select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as GroupBy)}
              className="text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
            >
              <option value="none">None</option>
              <option value="document_type">Document Type</option>
              <option value="status">Status</option>
              <option value="date">Date</option>
            </select>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center border border-gray-300 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode("list")}
              className={`p-2 ${
                viewMode === "list" ? "bg-blue-100 text-blue-600" : "text-gray-500 hover:bg-gray-100"
              }`}
              title="List View"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
            <button
              onClick={() => setViewMode("details")}
              className={`p-2 ${
                viewMode === "details" ? "bg-blue-100 text-blue-600" : "text-gray-500 hover:bg-gray-100"
              }`}
              title="Details View"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M3 3h14v2H3V3zm0 4h14v2H3V7zm0 4h10v2H3v-2zm0 4h14v2H3v-2z" />
              </svg>
            </button>
            <button
              onClick={() => setViewMode("grid")}
              className={`p-2 ${
                viewMode === "grid" ? "bg-blue-100 text-blue-600" : "text-gray-500 hover:bg-gray-100"
              }`}
              title="Grid View"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Tag Filter Pills */}
        {allTags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="text-sm text-gray-500">Filter by tag:</span>
            {allTags.slice(0, 10).map((tag) => (
              <button
                key={tag}
                onClick={() => toggleTag(tag)}
                className={`px-2 py-1 text-xs rounded-full transition-colors ${
                  selectedTags.includes(tag)
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {tag}
              </button>
            ))}
            {allTags.length > 10 && (
              <span className="text-xs text-gray-400">+{allTags.length - 10} more</span>
            )}
            {selectedTags.length > 0 && (
              <button
                onClick={() => setSelectedTags([])}
                className="text-xs text-red-600 hover:text-red-800"
              >
                Clear filters
              </button>
            )}
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex">
        {/* File List / Grid */}
        <div className={`flex-1 ${selectedFile ? "border-r border-gray-200" : ""}`}>
          {processedFiles.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <svg
                className="w-16 h-16 mx-auto mb-4 text-gray-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p className="text-lg font-medium">No files found</p>
              <p className="text-sm">
                {searchQuery || selectedTags.length > 0
                  ? "Try adjusting your filters"
                  : "Process some documents to see them here"}
              </p>
            </div>
          ) : viewMode === "details" ? (
            <DetailsView
              groupedFiles={groupedFiles}
              isGroupExpanded={isGroupExpanded}
              toggleGroup={toggleGroup}
              selectedFile={selectedFile}
              setSelectedFile={setSelectedFile}
              sortBy={sortBy}
              sortOrder={sortOrder}
              handleSort={handleSort}
            />
          ) : viewMode === "grid" ? (
            <GridView
              groupedFiles={groupedFiles}
              isGroupExpanded={isGroupExpanded}
              toggleGroup={toggleGroup}
              selectedFile={selectedFile}
              setSelectedFile={setSelectedFile}
            />
          ) : (
            <ListView
              groupedFiles={groupedFiles}
              isGroupExpanded={isGroupExpanded}
              toggleGroup={toggleGroup}
              selectedFile={selectedFile}
              setSelectedFile={setSelectedFile}
            />
          )}
        </div>

        {/* Detail Panel */}
        {selectedFile && (
          <DetailPanel file={selectedFile} onClose={() => setSelectedFile(null)} />
        )}
      </div>
    </div>
  );
}

// Details View (table-like)
function DetailsView({
  groupedFiles,
  isGroupExpanded,
  toggleGroup,
  selectedFile,
  setSelectedFile,
  sortBy,
  sortOrder,
  handleSort,
}: {
  groupedFiles: Record<string, ProcessedFile[]>;
  isGroupExpanded: (name: string) => boolean;
  toggleGroup: (name: string) => void;
  selectedFile: ProcessedFile | null;
  setSelectedFile: (file: ProcessedFile | null) => void;
  sortBy: SortBy;
  sortOrder: SortOrder;
  handleSort: (column: SortBy) => void;
}) {
  const renderSortHeader = (column: SortBy, label: string) => (
    <button
      onClick={() => handleSort(column)}
      className="flex items-center gap-1 hover:text-gray-900"
    >
      {label}
      {sortBy === column && (
        <span>{sortOrder === "asc" ? "↑" : "↓"}</span>
      )}
    </button>
  );

  return (
    <div className="max-h-[600px] overflow-y-auto">
      {/* Table Header */}
      <div className="sticky top-0 bg-gray-50 border-b border-gray-200 px-4 py-2 grid grid-cols-12 gap-4 text-sm font-medium text-gray-600">
        <div className="col-span-5">
          {renderSortHeader("name", "Name")}
        </div>
        <div className="col-span-2">
          {renderSortHeader("type", "Type")}
        </div>
        <div className="col-span-3">Tags</div>
        <div className="col-span-2">
          {renderSortHeader("status", "Status")}
        </div>
      </div>

      {/* Groups */}
      {Object.entries(groupedFiles).map(([groupName, files]) => (
        <div key={groupName}>
          {Object.keys(groupedFiles).length > 1 && (
            <button
              onClick={() => toggleGroup(groupName)}
              className="w-full px-4 py-2 bg-gray-100 hover:bg-gray-150 flex items-center gap-2 text-sm font-medium text-gray-700"
            >
              <span
                className={`transform transition-transform ${
                  isGroupExpanded(groupName) ? "rotate-90" : ""
                }`}
              >
                ▶
              </span>
              {groupName}
              <span className="text-gray-400 font-normal">({files.length})</span>
            </button>
          )}

          {(isGroupExpanded(groupName) || Object.keys(groupedFiles).length === 1) &&
            files.map((file, index) => {
              const fileIcon = getFileIcon(file.result?.document_type);
              const statusIcon = getStatusIcon(file.status);
              const isSelected = selectedFile?.name === file.name;

              return (
                <div
                  key={index}
                  onClick={() => setSelectedFile(isSelected ? null : file)}
                  className={`px-4 py-3 grid grid-cols-12 gap-4 items-center cursor-pointer border-b border-gray-100 hover:bg-blue-50 transition-colors ${
                    isSelected ? "bg-blue-100" : ""
                  }`}
                >
                  {/* Name */}
                  <div className="col-span-5 flex items-center gap-3 min-w-0">
                    <span
                      className={`w-8 h-8 flex items-center justify-center rounded ${fileIcon.color}`}
                    >
                      {fileIcon.icon}
                    </span>
                    <div className="min-w-0">
                      <p className="font-medium text-gray-900 truncate">
                        {file.result?.title || file.name}
                      </p>
                      <p className="text-xs text-gray-500 truncate">{file.name}</p>
                    </div>
                  </div>

                  {/* Type */}
                  <div className="col-span-2">
                    <span
                      className={`inline-block px-2 py-1 text-xs rounded ${fileIcon.color}`}
                    >
                      {file.result?.document_type || "—"}
                    </span>
                  </div>

                  {/* Tags */}
                  <div className="col-span-3 flex flex-wrap gap-1">
                    {file.result?.tags?.slice(0, 3).map((tag, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                    {(file.result?.tags?.length || 0) > 3 && (
                      <span className="text-xs text-gray-400">
                        +{file.result!.tags!.length - 3}
                      </span>
                    )}
                  </div>

                  {/* Status */}
                  <div className="col-span-2">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded ${statusIcon.color}`}
                    >
                      {statusIcon.icon} {file.status}
                    </span>
                  </div>
                </div>
              );
            })}
        </div>
      ))}
    </div>
  );
}

// List View (compact)
function ListView({
  groupedFiles,
  isGroupExpanded,
  toggleGroup,
  selectedFile,
  setSelectedFile,
}: {
  groupedFiles: Record<string, ProcessedFile[]>;
  isGroupExpanded: (name: string) => boolean;
  toggleGroup: (name: string) => void;
  selectedFile: ProcessedFile | null;
  setSelectedFile: (file: ProcessedFile | null) => void;
}) {
  return (
    <div className="max-h-[600px] overflow-y-auto">
      {Object.entries(groupedFiles).map(([groupName, files]) => (
        <div key={groupName}>
          {Object.keys(groupedFiles).length > 1 && (
            <button
              onClick={() => toggleGroup(groupName)}
              className="w-full px-4 py-2 bg-gray-100 hover:bg-gray-150 flex items-center gap-2 text-sm font-medium text-gray-700"
            >
              <span
                className={`transform transition-transform ${
                  isGroupExpanded(groupName) ? "rotate-90" : ""
                }`}
              >
                ▶
              </span>
              {groupName}
              <span className="text-gray-400 font-normal">({files.length})</span>
            </button>
          )}

          {(isGroupExpanded(groupName) || Object.keys(groupedFiles).length === 1) &&
            files.map((file, index) => {
              const fileIcon = getFileIcon(file.result?.document_type);
              const statusIcon = getStatusIcon(file.status);
              const isSelected = selectedFile?.name === file.name;

              return (
                <div
                  key={index}
                  onClick={() => setSelectedFile(isSelected ? null : file)}
                  className={`px-4 py-2 flex items-center gap-3 cursor-pointer border-b border-gray-100 hover:bg-blue-50 transition-colors ${
                    isSelected ? "bg-blue-100" : ""
                  }`}
                >
                  <span
                    className={`w-6 h-6 flex items-center justify-center rounded text-sm ${fileIcon.color}`}
                  >
                    {fileIcon.icon}
                  </span>
                  <span className="flex-1 text-sm text-gray-900 truncate">
                    {file.result?.title || file.name}
                  </span>
                  <span
                    className={`w-5 h-5 flex items-center justify-center rounded-full text-xs ${statusIcon.color}`}
                  >
                    {statusIcon.icon}
                  </span>
                </div>
              );
            })}
        </div>
      ))}
    </div>
  );
}

// Grid View (cards)
function GridView({
  groupedFiles,
  isGroupExpanded,
  toggleGroup,
  selectedFile,
  setSelectedFile,
}: {
  groupedFiles: Record<string, ProcessedFile[]>;
  isGroupExpanded: (name: string) => boolean;
  toggleGroup: (name: string) => void;
  selectedFile: ProcessedFile | null;
  setSelectedFile: (file: ProcessedFile | null) => void;
}) {
  return (
    <div className="max-h-[600px] overflow-y-auto p-4">
      {Object.entries(groupedFiles).map(([groupName, files]) => (
        <div key={groupName} className="mb-6">
          {Object.keys(groupedFiles).length > 1 && (
            <button
              onClick={() => toggleGroup(groupName)}
              className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-700"
            >
              <span
                className={`transform transition-transform ${
                  isGroupExpanded(groupName) ? "rotate-90" : ""
                }`}
              >
                ▶
              </span>
              {groupName}
              <span className="text-gray-400 font-normal">({files.length})</span>
            </button>
          )}

          {(isGroupExpanded(groupName) || Object.keys(groupedFiles).length === 1) && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {files.map((file, index) => {
                const fileIcon = getFileIcon(file.result?.document_type);
                const statusIcon = getStatusIcon(file.status);
                const isSelected = selectedFile?.name === file.name;

                return (
                  <div
                    key={index}
                    onClick={() => setSelectedFile(isSelected ? null : file)}
                    className={`p-4 border rounded-lg cursor-pointer hover:shadow-md transition-all ${
                      isSelected
                        ? "border-blue-500 bg-blue-50 shadow-md"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span
                        className={`w-10 h-10 flex items-center justify-center rounded-lg text-lg ${fileIcon.color}`}
                      >
                        {fileIcon.icon}
                      </span>
                      <span
                        className={`w-6 h-6 flex items-center justify-center rounded-full text-xs ${statusIcon.color}`}
                      >
                        {statusIcon.icon}
                      </span>
                    </div>
                    <h3 className="font-medium text-sm text-gray-900 truncate mb-1">
                      {file.result?.title || file.name}
                    </h3>
                    <p className="text-xs text-gray-500 truncate mb-2">{file.name}</p>
                    {file.result?.document_type && (
                      <span
                        className={`inline-block px-2 py-0.5 text-xs rounded ${fileIcon.color}`}
                      >
                        {file.result.document_type}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// Detail Panel (sidebar)
function DetailPanel({
  file,
  onClose,
}: {
  file: ProcessedFile;
  onClose: () => void;
}) {
  const fileIcon = getFileIcon(file.result?.document_type);
  const statusIcon = getStatusIcon(file.status);

  return (
    <div className="w-80 p-4 bg-gray-50">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-800">File Details</h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-200 rounded"
          title="Close"
        >
          <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* File Icon and Title */}
      <div className="text-center mb-6">
        <span
          className={`inline-flex w-16 h-16 items-center justify-center rounded-xl text-3xl ${fileIcon.color}`}
        >
          {fileIcon.icon}
        </span>
        <h4 className="mt-3 font-medium text-gray-900 break-words">
          {file.result?.title || file.name}
        </h4>
        <p className="text-sm text-gray-500 break-all">{file.name}</p>
      </div>

      {/* Status */}
      <div className="mb-4">
        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
          Status
        </label>
        <div className="mt-1">
          <span
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${statusIcon.color}`}
          >
            {statusIcon.icon} {file.status}
          </span>
        </div>
      </div>

      {/* Error Message */}
      {file.error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <label className="text-xs font-medium text-red-600 uppercase tracking-wide">
            Error
          </label>
          <p className="mt-1 text-sm text-red-700">{file.error}</p>
        </div>
      )}

      {/* Document Type */}
      {file.result?.document_type && (
        <div className="mb-4">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Document Type
          </label>
          <div className="mt-1">
            <span className={`inline-block px-3 py-1.5 rounded-full text-sm ${fileIcon.color}`}>
              {file.result.document_type}
            </span>
          </div>
        </div>
      )}

      {/* Tags */}
      {file.result?.tags && file.result.tags.length > 0 && (
        <div className="mb-4">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Tags
          </label>
          <div className="mt-2 flex flex-wrap gap-2">
            {file.result.tags.map((tag, i) => (
              <span
                key={i}
                className="px-2 py-1 text-sm bg-gray-200 text-gray-700 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Summary */}
      {file.result?.summary && (
        <div className="mb-4">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Summary
          </label>
          <p className="mt-1 text-sm text-gray-800">{file.result.summary}</p>
        </div>
      )}

      {/* Document Date */}
      {file.result?.date && (
        <div className="mb-4">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Document Date
          </label>
          <p className="mt-1 text-sm text-gray-800 font-medium">{file.result.date}</p>
        </div>
      )}

      {/* Title */}
      {file.result?.title && (
        <div className="mb-4">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Generated Title
          </label>
          <p className="mt-1 text-sm text-gray-800">{file.result.title}</p>
        </div>
      )}
    </div>
  );
}
