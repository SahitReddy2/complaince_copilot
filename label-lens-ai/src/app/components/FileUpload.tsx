'use client'
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function FileUpload() {
    const [file, setFile] = useState<File | null>(null);
    const [message, setMessage] = useState("");

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files[0]) {
            setFile(event.target.files[0]);
        }
    }

    const handleUpload = async () => {
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch(`${API_URL}/api/extract/analyze-document`, {
                method: 'POST',
                body: formData,
            });

            if (res.ok) {
                setMessage('File uploaded successfully');
            } else {
                setMessage(`Upload failed: HTTP ${res.status}`);
            }
        } catch (err: any) {
            setMessage(`Upload failed: ${err.message}`);
        }
    }

    return (
        <div className="p-4 border rounded-lg max-w-md mx-auto mt-8">
            <input type="file" onChange={handleFileChange} className="mb-4" />
            <button onClick={handleUpload} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
                Upload
            </button>
            {message && <p className="mt-2">{message}</p>}
        </div>
    )
}
