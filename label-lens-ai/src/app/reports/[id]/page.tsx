"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import Layout from "../../components/Layout";

interface Claim {
    claim_text: string;
    claim_type: string;
    severity: string;
}

interface Ingredient {
    ingredient_name: string;
    is_allergen: boolean;
    function?: string;
}

interface Compliance {
    law: string;
    confidence: number;
    reason: string;
    severity: string;
}

interface Report {
    id: number;
    filename: string;
    file_url:string;
    created_at: string;
    claims: Claim[];
    ingredients: Ingredient[];
    compliance: Compliance[];
}

export default function ReportDetailPage() {
    const { id } = useParams();
    const [report, setReport] = useState<Report | null>(null);
    const [loading, setLoading] = useState(true);
    const [textContent, setTextContent] = useState<string | null>(null);


    useEffect(() => {
        const fetchReport = async () => {
            const { data, error } = await supabase
                .from("reports")
                .select("*")
                .eq("id", id)
                .single();
            
            if (data && data.file_url && !data.file_url.startsWith("http")) {
                const { data: publicUrlData } = supabase
                    .storage
                    .from("reports")
                    .getPublicUrl(data.file_url);

                if (publicUrlData?.publicUrl) {
                    data.file_url = publicUrlData.publicUrl;
                }
            }
            console.log("🖼️ Final image URL:", data.file_url);
            if (error) {
                console.error("Failed to fetch report:", error.message)
            } else {
                setReport(data as Report);

                const pathname = new URL(data.file_url).pathname

                if (pathname.endsWith(".txt")){
                    try{
                        const response = await fetch(data.file_url);
                        const text = await response.text();
                        setTextContent(text);
                    } catch (e) {
                        console.error("Failed to load file")
                        setTextContent("Failed to load preview.")
                    }
                }
            }

            setLoading(false);
        };

        fetchReport();
    }, [id]);

    if (loading) return <p className="p-8">Loading report...</p>;
    if (!report) return <p className="p-8 text-red-600">Report not found!</p>

    return (
        <Layout>
            <div className="p-8 max-w-4xl mx-auto space-y-8">
                <h1 className="text-3xl font-bold text-slate-800">{report.filename}</h1>

                <p className="text-sm text-slate-500">
                Uploaded: {new Date(report.created_at).toLocaleString()}
                </p>

                {report.file_url && (
                    <div>
                        <h2 className="text-xl font-semibold mt-4">Uploaded File</h2>
                        <div className="mt-2 border rounded-md shadow-md p-2 bg-slate-50">
                            {report.file_url.match(/\.(jpg|jpeg|png|webp)$/i) ? (
                                <img
                                src={report.file_url}
                                alt="Uploaded File"
                                className="max-w-full rounded"
                                />
                            ) : report.file_url.includes(".pdf") ? (
                                <iframe
                                src={report.file_url}
                                title="PDF Preview"
                                className="w-full h-96 rounded"
                                />
                            ) : textContent !== null ? (
                                <pre className="whitespace-pre-wrap text-sm max-h-96 overflow-y-auto">
                                {textContent}
                                </pre>
                            ) : (
                                <p className="text-slate-600 italic">No preview available for this file type.</p>
                            )}
                        </div>
                    </div>
                )}

                <div>
                <h2 className="text-xl font-semibold mt-4">Claims</h2>
                {report.claims.length ? (
                    <div className="space-y-4 mt-2">
                    {report.claims.map((claim: any, idx: number) => (
                        <div key={idx} className="bg-white p-4 rounded-md shadow-sm border">
                            <div className="font-medium">{claim.claim_text}</div>
                        </div>
                    ))}
                    </div>
                ) : (
                    <p>No claims extracted.</p>
                )}
                </div>

                <div>
                <h2 className="text-xl font-semibold mt-4">Compliance Issues</h2>
                {report.compliance.length ? (
                    <div className="space-y-4 mt-2">
                    {report.compliance.map((issue: any, idx: number) => (
                        <div key={idx} className="bg-white p-4 rounded-md shadow-sm border">
                            <div className="font-semibold text-red-800">{issue.law}</div>
                            <div className="text-sm text-red-700 mt-1">{issue.reason}</div>
                            <div className="text-xs text-slate-500">
                                Confidence: {Math.round(issue.confidence * 100)}%
                                {issue.severity && (
                                    <span className="ml-4 font-medium text-yellow-600">
                                        Severity: {issue.severity.toUpperCase()}
                                    </span>
                                )}
                            </div>
                        </div>
                    ))}
                    </div>
                ) : (
                    <p className="text-green-700">No compliance issues found 🎉</p>
                )}
                </div>

                {report.ingredients?.length > 0 && (
                <div>
                    <h2 className="text-xl font-semibold mt-4">Ingredients</h2>
                    <ul className="list-disc list-inside space-y-1 mt-2">
                    {report.ingredients.map((ing: any, idx: number) => (
                        <li key={idx}>{ing.ingredient_name}</li>
                    ))}
                    </ul>
                </div>
                )}
            </div>
        </Layout>
    );
}