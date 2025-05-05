"use client"

import { useEffect, useState } from "react";
import api from "../../../services/api";
import { CacheEntryForm } from "./CacheEntryForm";
import { useRouter } from "next/navigation";

export default function CacheEntryDetail({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entry, setEntry] = useState<any>(null);

  useEffect(() => {
    const fetchEntry = async () => {
      try {
        const entry = await api.getCacheEntry(parseInt(params.id));
        setEntry(entry);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch cache entry");
      } finally {
        setLoading(false);
      }
    };
    fetchEntry();
  }, [params.id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading cache entry...</p>
        </div>
      </div>
    );
  }

  if (error || !entry) {
    return (
      <div className="p-8 max-w-2xl mx-auto">
        <div className="bg-red-50 text-red-600 p-3 rounded-md border border-red-200 text-sm">
          {error || "Cache entry not found."}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Cache Entry Details</h1>
      </div>
      <CacheEntryForm
        nlQuery={entry.nl_query}
        template={entry.template}
        templateType={entry.template_type}
        reasoningTrace={entry.reasoning_trace || ""}
        tags={entry.tags || []}
        readOnly={true}
        error={null}
      />
    </div>
  );
} 