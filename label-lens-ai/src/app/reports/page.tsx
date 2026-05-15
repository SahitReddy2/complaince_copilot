"use client";

import {useEffect, useState} from "react";
import Link from "next/link";
import {supabase} from "@/lib/supabase";
import Layout from "../components/Layout";

interface Report {
  id: number;
  filename: string;
  file_url: string;
  created_at: string;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReports = async () => {
      const { data, error } = await supabase
        .from("reports")
        .select("id, filename, file_url, created_at")
        .order("created_at", {ascending: false});
      
      if(error){
        console.error("Error fetching reports: ", error.message);
      } else {
        setReports(data || []);
      }

      setLoading(false);
    };

    fetchReports();
  }, []);

  const handleDelete = async (report: Report) => {
    const confirmed = confirm(`Are you sure you want to delete "${report.filename}"?`);
    if (!confirmed) return;

    // Delete from DB
    const { error: dbError } = await supabase
      .from("reports")
      .delete()
      .eq("id", report.id);

    if (dbError) {
      console.error("Failed to delete from DB:", dbError.message);
      alert("Failed to delete the report from the database.");
      return;
    }

    // Delete from Supabase Storage
    const filePath = report.file_url.split("/reports/")[1]; // get path after bucket
    if (filePath) {
      const { error: storageError } = await supabase
        .storage
        .from("reports")
        .remove([filePath]);

      if (storageError) {
        console.warn("Deleted from DB, but failed to delete from storage:", storageError.message);
      }
    }

    // Remove from UI
    setReports((prev) => prev.filter((r) => r.id !== report.id));
  };

  return (
    <Layout>
      <h1 className="text-2xl font-bold mb-6">Compliance Reports</h1>

      {loading ? (
        <p>Loading...</p>
      ) : reports.length === 0 ? (
        <p>No reports found.</p>
      ) : (
        <div className="space-y-4">
          {reports.map((report) => (
            <div key={report.id} className="border rounded-lg p-4 bg-white shadow-sm hover:shadow-md transition">
              <h2 className="text-lg font-semibold">{report.filename}</h2>
              <p className="text-sm text-gray-500">Created at: {new Date(report.created_at).toLocaleString()}</p>
              <div className="flex gap-4 mt-2">
                <Link href={`/reports/${report.id}`} className="text-blue-600 hover:underline">
                  View Report
                </Link>

                <a href={report.file_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                  View File
                </a>

                <button
                  onClick={() => handleDelete(report)}
                  className="text-red-600 hover:underline ml-auto"
                >
                  Resolve & Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )
      }
    </Layout>
  );
}
