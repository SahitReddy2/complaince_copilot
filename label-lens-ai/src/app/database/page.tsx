'use client';

import Image from "next/image";
import React from "react";
import Layout from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { HardDrivesIcon } from "@phosphor-icons/react";
import Link from "next/link"

const lawDatabses = [
  {
    id: 'ftc',
    name: 'FTC Marketing Guidelines Database',
    description: 'Federal regulations on marketing',
    coverage: 'US Federal',
    status: 'Operational',
    lastChanged: '2025-08-01 12:00',
    pdf: `/laws/Advertising FAQ's_ A Guide for Small Business.pdf`
  },
  {
    id: 'fda',
    name: 'FDA Compliance Database',
    description: 'Federal regulations for cosmetics',
    coverage: 'US Federal',
    status: 'Operational',
    lastChanged: '2025-08-01 12:00',
    pdf: `/laws/cosmetics law.pdf`
  },
  {
    id: 'labeling',
    name: 'Cosmetics Labeling Guide',
    description: 'Federal guidelines on labeling requirements',
    coverage: 'US Federal',
    status: 'Operational',
    lastChanged: '2025-08-01 12:00',
    pdf: `/laws/Cosmetics-Labeling-Guide.pdf`
  },
  {
    id: 'health',
    name: 'Health Guidelines',
    description: 'Federal guidelines on health requirements',
    coverage: 'US Federal',
    status: 'Operational',
    lastChanged: '2025-08-01 12:00',
    pdf: `/laws/Health-Guidance-508.pdf`
  },
  {
    id: 'MoCRA',
    name: 'MoCRA Database',
    description: 'MoCRA regulations on cosmetics',
    coverage: 'US Federal',
    status: 'Operational',
    lastChanged: '2025-08-01 12:00',
    pdf: `/laws/MoCRA-Omnibus-12.20.22-1.pdf`
  },
  {
    id: 'p65',
    name: 'Prop65 Database',
    description: 'Banned Ingredients List of Prop65',
    coverage: 'Californa, USA',
    status: 'Limited Access',
    lastChanged: '2025-08-01 12:00',
    pdf: `/laws/p65chemicalslist.pdf`
  }
]

export default function databasesPage() {
  return (
    <Layout>
      <div className="max-w-5xl mx-auto py-10 px-4 space-y-6">
        <h1 className="text-3xl font-bold text-slate-900">Legal Database Connections</h1>
        <p className="text-slate-600 text-md">
          View and Monitor connections to regulations and compliance databases
        </p>

        {lawDatabses.map((doc) => (
          <Card key={doc.id} className="border border-slate-300 shadow-md">
            <CardHeader className="flex flex-col md:flex-row justify-between items-start md:items-center">
              <div className="flex gap-3 items-start md:items-center">
                <HardDrivesIcon className="w-6 h-6 text-slate-700 mt-1" />
                <div>
                  <CardTitle className="text-lg font-semibold text-slate-800">
                    {doc.name}
                  </CardTitle>
                  <p className="text-sm text-slate-600">{doc.description}</p>
                  <p className="text-xs text-slate-500 mt-1">Coverage: {doc.coverage}</p>
                  <p className="text-xs text-slate-500">Last Sync: {doc.lastChanged}</p>
                </div>
              </div>
              <div className="mt-4 md:mt-0 flex gap-2">
                <Button variant="outline" asChild>
                  <a href={doc.pdf} target="_blank" rel="noopener noreferrer">View PDF</a>
                </Button>
                <Button variant={doc.status === 'Operational' ? 'default' : 'secondary'}>
                  {doc.status}
                </Button>
              </div>
            </CardHeader>
          </Card>
        ))}
      </div>
    </Layout>
  )
}
