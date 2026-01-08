"use client";

import { useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api";
import type { DocumentListItem } from "@/lib/types";

type ViewMode = "list" | "grid" | "details";
type GroupBy = "none" | "document_type" | "date";
type SortBy = "name" | "type" | "date" | "size";
type SortOrder = "asc" | "desc";

// File type icons mapping
const getFileIcon = (type?: string | null) => {
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

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const formatDate = (dateStr: string): string => {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
};

const formatDateShort = (dateStr: string): string => {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
};

export function DocumentListExplorer() {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [viewMode, setViewMode] = useState<ViewMode>("details");
  const [groupBy, setGroupBy] = useState<GroupBy>("none");
  const [sortBy, setSortBy] = useState<SortBy>("date");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedEntities, setSelectedEntities] = useState<string[]>([]);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [selectedDoc, setSelectedDoc] = useState<DocumentListItem | null>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const data = await api.listDocuments(100);
      setDocuments(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  };

  // Open document in new tab
  const handleOpenDocument = (doc: DocumentListItem) => {
    api.openDocument(doc.path);
  };

  // Extract all unique tags from documents
  const allTags = useMemo(() => {
    const tags = new Set<string>();
    documents.forEach((doc) => {
      doc.tags?.forEach((tag) => tags.add(tag));
    });
    return Array.from(tags).sort();
  }, [documents]);

  // Extract all unique document types
  const allDocTypes = useMemo(() => {
    const types = new Set<string>();
    documents.forEach((doc) => {
      if (doc.document_type) {
        types.add(doc.document_type);
      }
    });
    return Array.from(types).sort();
  }, [documents]);

  // Extract all unique entities (people, organizations)
  const allEntities = useMemo(() => {
    const entities = new Set<string>();
    documents.forEach((doc) => {
      doc.entities?.forEach((entity) => entities.add(entity));
    });
    return Array.from(entities).sort();
  }, [documents]);

  // Filter and sort documents
  const processedDocs = useMemo(() => {
    let result = [...documents];

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (doc) =>
          doc.path.toLowerCase().includes(query) ||
          doc.title?.toLowerCase().includes(query) ||
          doc.document_type?.toLowerCase().includes(query) ||
          doc.tags?.some((tag) => tag.toLowerCase().includes(query)) ||
          doc.entities?.some((entity) => entity.toLowerCase().includes(query))
      );
    }

    // Apply tag filter
    if (selectedTags.length > 0) {
      result = result.filter((doc) =>
        selectedTags.every((tag) => doc.tags?.includes(tag))
      );
    }

    // Apply type filter
    if (selectedTypes.length > 0) {
      result = result.filter((doc) =>
        selectedTypes.includes(doc.document_type || "")
      );
    }

    // Apply entity filter
    if (selectedEntities.length > 0) {
      result = result.filter((doc) =>
        selectedEntities.some((entity) => doc.entities?.includes(entity))
      );
    }

    // Sort documents
    result.sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case "name":
          comparison = (a.title || a.path).localeCompare(b.title || b.path);
          break;
        case "type":
          comparison = (a.document_type || "").localeCompare(b.document_type || "");
          break;
        case "date":
          // Use document_date if available, otherwise fall back to processed_at
          const dateA = a.document_date || a.processed_at;
          const dateB = b.document_date || b.processed_at;
          comparison = new Date(dateA).getTime() - new Date(dateB).getTime();
          break;
        case "size":
          comparison = a.size_bytes - b.size_bytes;
          break;
      }
      return sortOrder === "asc" ? comparison : -comparison;
    });

    return result;
  }, [documents, searchQuery, selectedTags, selectedTypes, selectedEntities, sortBy, sortOrder]);

  // Group documents
  const groupedDocs = useMemo(() => {
    if (groupBy === "none") {
      return { "All Documents": processedDocs };
    }

    const groups: Record<string, DocumentListItem[]> = {};

    processedDocs.forEach((doc) => {
      let groupKey: string;
      switch (groupBy) {
        case "document_type":
          groupKey = doc.document_type || "Unknown";
          break;
        case "date":
          // Use the document date extracted by LLM if available, otherwise fall back to processed_at
          if (doc.document_date) {
            // Format: YYYY-MM-DD -> display as Month YYYY
            const dateParts = doc.document_date.split("-");
            if (dateParts.length === 3) {
              const [year, month] = dateParts;
              const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
              const monthIdx = parseInt(month, 10) - 1;
              groupKey = `${monthNames[monthIdx] || month} ${year}`;
            } else {
              groupKey = doc.document_date;
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
      groups[groupKey].push(doc);
    });

    // Sort groups by date (newest first) if grouping by date
    if (groupBy === "date") {
      const sortedGroups: Record<string, DocumentListItem[]> = {};
      const groupNames = Object.keys(groups).sort((a, b) => {
        if (a === "No Date") return 1;
        if (b === "No Date") return -1;
        // Parse "Mon YYYY" format and sort descending
        const parseGroup = (g: string) => {
          const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
          const parts = g.split(" ");
          if (parts.length === 2) {
            const monthIdx = monthNames.indexOf(parts[0]);
            const year = parseInt(parts[1], 10);
            return year * 12 + monthIdx;
          }
          return 0;
        };
        return parseGroup(b) - parseGroup(a);
      });
      groupNames.forEach((name) => {
        sortedGroups[name] = groups[name];
      });
      return sortedGroups;
    }

    return groups;
  }, [processedDocs, groupBy]);

  const toggleGroup = (groupName: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupName)) {
      newExpanded.delete(groupName);
    } else {
      newExpanded.add(groupName);
    }
    setExpandedGroups(newExpanded);
  };

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const toggleType = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const toggleEntity = (entity: string) => {
    setSelectedEntities((prev) =>
      prev.includes(entity) ? prev.filter((e) => e !== entity) : [...prev, entity]
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

  const clearFilters = () => {
    setSearchQuery("");
    setSelectedTags([]);
    setSelectedTypes([]);
    setSelectedEntities([]);
  };

  // Initialize all groups as expanded
  useEffect(() => {
    if (Object.keys(groupedDocs).length > 0) {
      setExpandedGroups(new Set(Object.keys(groupedDocs)));
    }
  }, [groupedDocs]);

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">
          Document Archive
        </h2>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">
          Document Archive
        </h2>
        <div className="text-red-600 dark:text-red-400">{error}</div>
      </div>
    );
  }

  const hasFilters = searchQuery || selectedTags.length > 0 || selectedTypes.length > 0 || selectedEntities.length > 0;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
      {/* Header / Toolbar */}
      <div className="border-b border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
            Document Archive
          </h2>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {processedDocs.length} document{processedDocs.length !== 1 ? "s" : ""}
            </span>
            <button
              onClick={loadDocuments}
              className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 flex items-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
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
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
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
            <label className="text-sm text-gray-600 dark:text-gray-400">Group:</label>
            <select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as GroupBy)}
              className="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="none">None</option>
              <option value="document_type">Document Type</option>
              <option value="date">Date</option>
            </select>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode("list")}
              className={`p-2 ${
                viewMode === "list"
                  ? "bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300"
                  : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
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
                viewMode === "details"
                  ? "bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300"
                  : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
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
                viewMode === "grid"
                  ? "bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300"
                  : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
              title="Grid View"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="mt-3 space-y-2">
          {/* Document Type Filter */}
          {allDocTypes.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-gray-500 dark:text-gray-400">Type:</span>
              {allDocTypes.map((type) => (
                <button
                  key={type}
                  onClick={() => toggleType(type)}
                  className={`px-2 py-1 text-xs rounded-full transition-colors ${
                    selectedTypes.includes(type)
                      ? "bg-purple-600 text-white"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          )}

          {/* Tag Filter */}
          {allTags.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-gray-500 dark:text-gray-400">Tags:</span>
              {allTags.slice(0, 12).map((tag) => (
                <button
                  key={tag}
                  onClick={() => toggleTag(tag)}
                  className={`px-2 py-1 text-xs rounded-full transition-colors ${
                    selectedTags.includes(tag)
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                  }`}
                >
                  {tag}
                </button>
              ))}
              {allTags.length > 12 && (
                <span className="text-xs text-gray-400">+{allTags.length - 12} more</span>
              )}
            </div>
          )}

          {/* Entity/Person Filter */}
          {allEntities.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-gray-500 dark:text-gray-400">People/Orgs:</span>
              {allEntities.slice(0, 10).map((entity) => (
                <button
                  key={entity}
                  onClick={() => toggleEntity(entity)}
                  className={`px-2 py-1 text-xs rounded-full transition-colors ${
                    selectedEntities.includes(entity)
                      ? "bg-green-600 text-white"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                  }`}
                >
                  {entity}
                </button>
              ))}
              {allEntities.length > 10 && (
                <span className="text-xs text-gray-400">+{allEntities.length - 10} more</span>
              )}
            </div>
          )}

          {hasFilters && (
            <button
              onClick={clearFilters}
              className="text-xs text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
            >
              ✕ Clear all filters
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex">
        {/* Document List / Grid */}
        <div className={`flex-1 ${selectedDoc ? "border-r border-gray-200 dark:border-gray-700" : ""}`}>
          {processedDocs.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              <svg
                className="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600"
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
              <p className="text-lg font-medium">No documents found</p>
              <p className="text-sm">
                {hasFilters
                  ? "Try adjusting your filters"
                  : "Process some PDFs to see them here"}
              </p>
            </div>
          ) : viewMode === "details" ? (
            <DetailsView
              groupedDocs={groupedDocs}
              expandedGroups={expandedGroups}
              toggleGroup={toggleGroup}
              selectedDoc={selectedDoc}
              setSelectedDoc={setSelectedDoc}
              sortBy={sortBy}
              sortOrder={sortOrder}
              handleSort={handleSort}
              onOpenDocument={handleOpenDocument}
            />
          ) : viewMode === "grid" ? (
            <GridView
              groupedDocs={groupedDocs}
              expandedGroups={expandedGroups}
              toggleGroup={toggleGroup}
              selectedDoc={selectedDoc}
              setSelectedDoc={setSelectedDoc}
              onOpenDocument={handleOpenDocument}
            />
          ) : (
            <ListView
              groupedDocs={groupedDocs}
              expandedGroups={expandedGroups}
              toggleGroup={toggleGroup}
              selectedDoc={selectedDoc}
              setSelectedDoc={setSelectedDoc}
              onOpenDocument={handleOpenDocument}
            />
          )}
        </div>

        {/* Detail Panel */}
        {selectedDoc && (
          <DetailPanel doc={selectedDoc} onClose={() => setSelectedDoc(null)} />
        )}
      </div>
    </div>
  );
}

// Details View (table-like)
function DetailsView({
  groupedDocs,
  expandedGroups,
  toggleGroup,
  selectedDoc,
  setSelectedDoc,
  sortBy,
  sortOrder,
  handleSort,
  onOpenDocument,
}: {
  groupedDocs: Record<string, DocumentListItem[]>;
  expandedGroups: Set<string>;
  toggleGroup: (name: string) => void;
  selectedDoc: DocumentListItem | null;
  setSelectedDoc: (doc: DocumentListItem | null) => void;
  sortBy: SortBy;
  sortOrder: SortOrder;
  handleSort: (column: SortBy) => void;
  onOpenDocument: (doc: DocumentListItem) => void;
}) {
  const renderSortHeader = (column: SortBy, label: string) => (
    <button
      onClick={() => handleSort(column)}
      className="flex items-center gap-1 hover:text-gray-900 dark:hover:text-white"
    >
      {label}
      {sortBy === column && <span>{sortOrder === "asc" ? "↑" : "↓"}</span>}
    </button>
  );

  return (
    <div className="max-h-[600px] overflow-y-auto">
      {/* Table Header */}
      <div className="sticky top-0 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-2 grid grid-cols-12 gap-4 text-sm font-medium text-gray-600 dark:text-gray-400">
        <div className="col-span-4">
          {renderSortHeader("name", "Name")}
        </div>
        <div className="col-span-2">
          {renderSortHeader("type", "Type")}
        </div>
        <div className="col-span-3">Tags</div>
        <div className="col-span-2">
          {renderSortHeader("date", "Date")}
        </div>
        <div className="col-span-1">
          {renderSortHeader("size", "Size")}
        </div>
      </div>

      {/* Groups */}
      {Object.entries(groupedDocs).map(([groupName, docs]) => (
        <div key={groupName}>
          {Object.keys(groupedDocs).length > 1 && (
            <button
              onClick={() => toggleGroup(groupName)}
              className="w-full px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-150 dark:hover:bg-gray-750 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              <span
                className={`transform transition-transform ${
                  expandedGroups.has(groupName) ? "rotate-90" : ""
                }`}
              >
                ▶
              </span>
              {groupName}
              <span className="text-gray-400 font-normal">({docs.length})</span>
            </button>
          )}

          {(expandedGroups.has(groupName) || Object.keys(groupedDocs).length === 1) &&
            docs.map((doc, index) => {
              const fileIcon = getFileIcon(doc.document_type);
              const isSelected = selectedDoc?.path === doc.path;

              return (
                <div
                  key={index}
                  onClick={() => setSelectedDoc(isSelected ? null : doc)}
                  onDoubleClick={() => onOpenDocument(doc)}
                  className={`px-4 py-3 grid grid-cols-12 gap-4 items-center cursor-pointer border-b border-gray-100 dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors ${
                    isSelected ? "bg-blue-100 dark:bg-blue-900/30" : ""
                  }`}
                >
                  {/* Name */}
                  <div className="col-span-4 flex items-center gap-3 min-w-0">
                    <span
                      className={`w-8 h-8 flex items-center justify-center rounded ${fileIcon.color}`}
                    >
                      {fileIcon.icon}
                    </span>
                    <div className="min-w-0">
                      <p className="font-medium text-gray-900 dark:text-white truncate">
                        {doc.title || doc.path.split("/").pop()}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {doc.path.split("/").pop()}
                      </p>
                    </div>
                  </div>

                  {/* Type */}
                  <div className="col-span-2">
                    <span className={`inline-block px-2 py-1 text-xs rounded ${fileIcon.color}`}>
                      {doc.document_type || "—"}
                    </span>
                  </div>

                  {/* Tags */}
                  <div className="col-span-3 flex flex-wrap gap-1">
                    {doc.tags?.slice(0, 3).map((tag, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                    {(doc.tags?.length || 0) > 3 && (
                      <span className="text-xs text-gray-400">+{doc.tags!.length - 3}</span>
                    )}
                  </div>

                  {/* Date - prefer document date over processed date */}
                  <div className="col-span-2 text-sm text-gray-600 dark:text-gray-400" title={doc.document_date ? `Document date: ${doc.document_date}` : `Processed: ${formatDateShort(doc.processed_at)}`}>
                    {doc.document_date || formatDateShort(doc.processed_at)}
                  </div>

                  {/* Size + Open Button */}
                  <div className="col-span-1 flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {formatFileSize(doc.size_bytes)}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpenDocument(doc);
                      }}
                      className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                      title="Open document"
                    >
                      <svg className="w-4 h-4 text-gray-500 hover:text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </button>
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
  groupedDocs,
  expandedGroups,
  toggleGroup,
  selectedDoc,
  setSelectedDoc,
  onOpenDocument,
}: {
  groupedDocs: Record<string, DocumentListItem[]>;
  expandedGroups: Set<string>;
  toggleGroup: (name: string) => void;
  selectedDoc: DocumentListItem | null;
  setSelectedDoc: (doc: DocumentListItem | null) => void;
  onOpenDocument: (doc: DocumentListItem) => void;
}) {
  return (
    <div className="max-h-[600px] overflow-y-auto">
      {Object.entries(groupedDocs).map(([groupName, docs]) => (
        <div key={groupName}>
          {Object.keys(groupedDocs).length > 1 && (
            <button
              onClick={() => toggleGroup(groupName)}
              className="w-full px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-150 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              <span
                className={`transform transition-transform ${
                  expandedGroups.has(groupName) ? "rotate-90" : ""
                }`}
              >
                ▶
              </span>
              {groupName}
              <span className="text-gray-400 font-normal">({docs.length})</span>
            </button>
          )}

          {(expandedGroups.has(groupName) || Object.keys(groupedDocs).length === 1) &&
            docs.map((doc, index) => {
              const fileIcon = getFileIcon(doc.document_type);
              const isSelected = selectedDoc?.path === doc.path;

              return (
                <div
                  key={index}
                  onClick={() => setSelectedDoc(isSelected ? null : doc)}
                  onDoubleClick={() => onOpenDocument(doc)}
                  className={`px-4 py-2 flex items-center gap-3 cursor-pointer border-b border-gray-100 dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors ${
                    isSelected ? "bg-blue-100 dark:bg-blue-900/30" : ""
                  }`}
                >
                  <span className={`w-6 h-6 flex items-center justify-center rounded text-sm ${fileIcon.color}`}>
                    {fileIcon.icon}
                  </span>
                  <span className="flex-1 text-sm text-gray-900 dark:text-white truncate">
                    {doc.title || doc.path.split("/").pop()}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {formatFileSize(doc.size_bytes)}
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
  groupedDocs,
  expandedGroups,
  toggleGroup,
  selectedDoc,
  setSelectedDoc,
  onOpenDocument,
}: {
  groupedDocs: Record<string, DocumentListItem[]>;
  expandedGroups: Set<string>;
  toggleGroup: (name: string) => void;
  selectedDoc: DocumentListItem | null;
  setSelectedDoc: (doc: DocumentListItem | null) => void;
  onOpenDocument: (doc: DocumentListItem) => void;
}) {
  return (
    <div className="max-h-[600px] overflow-y-auto p-4">
      {Object.entries(groupedDocs).map(([groupName, docs]) => (
        <div key={groupName} className="mb-6">
          {Object.keys(groupedDocs).length > 1 && (
            <button
              onClick={() => toggleGroup(groupName)}
              className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              <span
                className={`transform transition-transform ${
                  expandedGroups.has(groupName) ? "rotate-90" : ""
                }`}
              >
                ▶
              </span>
              {groupName}
              <span className="text-gray-400 font-normal">({docs.length})</span>
            </button>
          )}

          {(expandedGroups.has(groupName) || Object.keys(groupedDocs).length === 1) && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {docs.map((doc, index) => {
                const fileIcon = getFileIcon(doc.document_type);
                const isSelected = selectedDoc?.path === doc.path;

                return (
                  <div
                    key={index}
                    onClick={() => setSelectedDoc(isSelected ? null : doc)}
                    onDoubleClick={() => onOpenDocument(doc)}
                    className={`p-4 border rounded-lg cursor-pointer hover:shadow-md transition-all ${
                      isSelected
                        ? "border-blue-500 bg-blue-50 dark:bg-blue-900/30 shadow-md"
                        : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className={`w-10 h-10 flex items-center justify-center rounded-lg text-lg ${fileIcon.color}`}>
                        {fileIcon.icon}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {formatFileSize(doc.size_bytes)}
                      </span>
                    </div>
                    <h3 className="font-medium text-sm text-gray-900 dark:text-white truncate mb-1">
                      {doc.title || doc.path.split("/").pop()}
                    </h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate mb-2">
                      {doc.path.split("/").pop()}
                    </p>
                    {doc.document_type && (
                      <span className={`inline-block px-2 py-0.5 text-xs rounded ${fileIcon.color}`}>
                        {doc.document_type}
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
function DetailPanel({ doc, onClose }: { doc: DocumentListItem; onClose: () => void }) {
  const fileIcon = getFileIcon(doc.document_type);

  const handleOpenDocument = () => {
    api.openDocument(doc.path);
  };

  return (
    <div className="w-80 p-4 bg-gray-50 dark:bg-gray-900">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-800 dark:text-white">Document Details</h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
          title="Close"
        >
          <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Open Button */}
      <button
        onClick={handleOpenDocument}
        className="w-full mb-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg flex items-center justify-center gap-2 transition-colors"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
        Open Document
      </button>

      {/* File Icon and Title */}
      <div className="text-center mb-6">
        <span className={`inline-flex w-16 h-16 items-center justify-center rounded-xl text-3xl ${fileIcon.color}`}>
          {fileIcon.icon}
        </span>
        <h4 className="mt-3 font-medium text-gray-900 dark:text-white break-words">
          {doc.title || doc.path.split("/").pop()}
        </h4>
        <p className="text-sm text-gray-500 dark:text-gray-400 break-all">
          {doc.path.split("/").pop()}
        </p>
      </div>

      {/* Document Type */}
      {doc.document_type && (
        <div className="mb-4">
          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Document Type
          </label>
          <div className="mt-1">
            <span className={`inline-block px-3 py-1.5 rounded-full text-sm ${fileIcon.color}`}>
              {doc.document_type}
            </span>
          </div>
        </div>
      )}

      {/* Tags */}
      {doc.tags && doc.tags.length > 0 && (
        <div className="mb-4">
          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Tags
          </label>
          <div className="mt-2 flex flex-wrap gap-2">
            {doc.tags.map((tag, i) => (
              <span
                key={i}
                className="px-2 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Entities (People/Organizations) */}
      {doc.entities && doc.entities.length > 0 && (
        <div className="mb-4">
          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            People / Organizations
          </label>
          <div className="mt-2 flex flex-wrap gap-2">
            {doc.entities.map((entity, i) => (
              <span
                key={i}
                className="px-2 py-1 text-sm bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full"
              >
                {entity}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Summary */}
      {doc.summary && (
        <div className="mb-4">
          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Summary
          </label>
          <p className="mt-1 text-sm text-gray-800 dark:text-gray-200">
            {doc.summary}
          </p>
        </div>
      )}

      {/* Document Date - the important date from the document content */}
      {doc.document_date && (
        <div className="mb-4">
          <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Document Date
          </label>
          <p className="mt-1 text-sm text-gray-800 dark:text-gray-200 font-medium">
            {doc.document_date}
          </p>
        </div>
      )}

      {/* File Size */}
      <div className="mb-4">
        <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          File Size
        </label>
        <p className="mt-1 text-sm text-gray-800 dark:text-gray-200">
          {formatFileSize(doc.size_bytes)}
        </p>
      </div>

      {/* Processed Date */}
      <div className="mb-4">
        <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          Processed
        </label>
        <p className="mt-1 text-sm text-gray-800 dark:text-gray-200">
          {formatDate(doc.processed_at)}
        </p>
      </div>

      {/* File Path */}
      <div className="mb-4">
        <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          Archive Path
        </label>
        <p className="mt-1 text-xs text-gray-600 dark:text-gray-400 break-all font-mono">
          {doc.path}
        </p>
      </div>
    </div>
  );
}
