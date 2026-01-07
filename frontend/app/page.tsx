import { StatusCard } from "@/components/StatusCard";
import { FileUpload } from "@/components/FileUpload";
import { DocumentListExplorer } from "@/components/DocumentListExplorer";
import { BatchProcessingPanel } from "@/components/BatchProcessingPanel";

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            DocTagger
          </h1>
          <p className="text-gray-600 dark:text-gray-300">
            Automatically tag and organize PDF documents using local LLM
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-1">
            <StatusCard />
          </div>
          <div className="lg:col-span-2">
            <FileUpload />
          </div>
        </div>

        {/* Batch Processing Panel */}
        <div className="mb-8">
          <BatchProcessingPanel />
        </div>

        <div>
          <DocumentListExplorer />
        </div>

        <footer className="mt-12 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>
            Powered by{" "}
            <a
              href="https://ollama.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              Ollama
            </a>{" "}
            and{" "}
            <a
              href="https://ocrmypdf.readthedocs.io"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              OCRmyPDF
            </a>
          </p>
        </footer>
      </div>
    </div>
  );
}
