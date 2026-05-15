'use client'
import { use, useState } from "react";

export default function FileUpload() {
    
    const [file, setFile] = useState<File | null>(null);
    const [message, setMessage] = useState("");

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if(event.target.files && event.target.files[0]){
            setFile(event.target.files[0]);
        }
    }

    const handleUpload = async () => {
        if(!file){
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch('http://localhost:3000/upload', {
            method: 'POST',
            body: formData
        })

        if(res.ok){
            setMessage('File uploaded successfully');
        } else {
            setMessage('File upload failed');
        }
    }

    return (
        <div className="p-4 border rounded-lg max-w-md mx-auto mt-8">
            <input type="file" onChange={handleFileChange} className="mb-4"/>
            <button onClick={handleUpload} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">Upload</button>
            {message && <p className="mt-2">{message}</p>}
        </div>
    )
}
