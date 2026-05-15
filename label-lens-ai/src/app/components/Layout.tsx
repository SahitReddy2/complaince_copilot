import React from "react";
import Navbar  from "./Navbar";
import '@/app/globals.css';

interface LayoutProps {
    children: React.ReactNode;
}

const Layout = ({ children }: LayoutProps) => {
    return (
        <div className="w-full min-h-screen">
            <Navbar />
            <main className="w-full px-4 sm:px-6 lg:px-12 py-8">
                {children}
            </main>
        </div>
        
    );
};

export default Layout;