'use client';

import React from "react";
import Layout from "../components/Layout";
import {Button} from "@/app/components/ui/button";
import {UserCircleIcon, BellSimpleRingingIcon, FingerprintIcon, CreditCardIcon } from "@phosphor-icons/react";


const Settings = () => {
    const Sections  = [
        {
            icon: <UserCircleIcon className="w-10 h-10" weight="bold"/>,
            title: 'Account Settings',
            description: 'Manage your account details.',
            action: 'Edit Profile'
        },
        {
            icon: <BellSimpleRingingIcon className="w-10 h-10" weight="bold"/>,
            title: 'Account Settings',
            description: 'Configure email and system notifications.',
            action: 'Manage Notifications'
        },
        {
            icon: <FingerprintIcon className="w-10 h-10" weight="bold"/>,
            title: 'Account Settings',
            description: 'Update password and security settings.',
            action: 'Security Settings'
        },
        {
            icon: <CreditCardIcon className="w-10 h-10" weight="bold"/>,
            title: 'Account Settings',
            description: 'Manage subscription and payment methods.',
            action: 'View Billing'
        }
    ];

    return (
        <Layout>
            {/* Main Headers */}
            <div className="max-w-4xl mx-auto">
                <div className="mb-8">
                    <h1 className="text-4xl font-bold text-slate-900 mb-2">
                        Settings
                    </h1>
                    <p className="text-lg text-slate-600">
                        Manage your account settings and preferences.
                    </p>
                </div>

                {/* Individual Settings */}
                <div className="space-y-6">
                    {Sections.map((section, index) => (
                        <div key={index} className="bg-white rounded-lg border border-slate-200  p-6 hover:shadow-md transition-shadow">
                            <div className="flex items-center justify-between">
                                <div className="flex items-start space-x-4">
                                    <div className="flex-shrink-0 mt-1">
                                        {section.icon}
                                    </div>
                                    <div>
                                        <h2 className="text-lg font-semibold text-slate-800 mb-1">
                                            {section.title}
                                        </h2>
                                        <p className="text-sm text-slate-600">
                                            {section.description}
                                        </p>
                                    </div>
                                </div>
                                <Button variant={"outline"} className="border-slate-300 text-slate-700 hover:bg-slate-50">{section.action}</Button>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Extra Settings */}
                <div className="mt-12 bg-slate-50 rounded-lg p-8">
                    <h3 className="text-lg font-semibold text-slate-800 mb-4">Support & Resources</h3>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <h4 className="font-medium text-slate-700 mb-2">Documentation</h4>
                            <p className="text-sm text-slate-600">Learn how to use Label Lens AI.</p>
                            <Button variant={"default"} className="text-neutral-300 hover:text-white mt-2" size={"sm"}>Learn More</Button>
                        </div>
                        <div>
                            <h4 className="font-medium text-slate-700 mb-2">Contact Support</h4>
                            <p className="text-sm text-slate-600">Get Help</p>
                            <Button variant={"default"} className="text-neutral-300 hover:text-white mt-2" size={"sm"} >Contact Us</Button>
                        </div>
                    </div>
                </div>
            </div>       
        </Layout>
    );
};

export default Settings;