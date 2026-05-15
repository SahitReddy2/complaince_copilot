'use client';

import React from "react";
import { useEffect, useState } from "react";
import Layout from "@/app/components/Layout";
import {Button} from "@/app/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle} from "@/app/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/app/components/ui/alert";
import { Badge } from "@/app/components/ui/badge";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { supabase } from "@/lib/supabase";
import {
  WarningCircleIcon,
  SecurityCameraIcon,
  HourglassSimpleIcon,
  CheckFatIcon,
  AsteriskIcon,
  WarningIcon,
  XIcon,
  FileLockIcon,
  FileTextIcon,
} from "@phosphor-icons/react";
import { ReceiptRussianRuble } from "lucide-react";

const Home =() => {

  const pathname = usePathname();
   
  //Changed to Real Data
  const [complianceScore, setComplianceScore] = useState(0);
  const [issueCounts, setIssueCounts] = useState({
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    resolved: 0,
  });
  const [recentIssues, setRecentIssues] = useState<any[]>([]);
  const [issueName, setIssueName] = useState<any[]>([]);
  const [scoreChange, setScoreChange] = useState(0);


  useEffect(() => {
    const fetchLatestReport = async () => {
      const { data, error } = await supabase
        .from("reports")
        .select("*")
        .order("created_at", { ascending: false })
        .select("*")
        .order("created_at", { ascending: false });


      if (error) {
        console.error("Report Fetch Failed:", error);
        return;
      }

      if (data && data.length > 0) {
        let totalCounts = {
          critical: 0,
          high: 0,
          medium: 0,
          low: 0,
          resolved: 0,
        };

        let totalScore = 0;
        let totalReports = 0;
        const recent = data[0];

        data.forEach((report) => {
          const counts = report.issue_counts || {};
          totalCounts.critical += counts.critical || 0;
          totalCounts.high += counts.high || 0;
          totalCounts.medium += counts.medium || 0;
          totalCounts.low += counts.low || 0;
          totalCounts.resolved += counts.resolved || 0;

          if (report.compliance_score !== undefined) {
            totalScore += report.compliance_score;
            totalReports += 1;
          }
        });

        const avgScore = totalReports > 0 ? Math.round(totalScore / totalReports) : 100;

        setComplianceScore(avgScore);
        setIssueCounts(totalCounts);
        setRecentIssues(recent.recent_issues || []);
        setIssueName(recent.filename || "");

        if (data.length > 1) {
          const delta = (recent.compliance_score || 0) - (data[1].compliance_score || 0);
          setScoreChange(delta);
        } else {
          setScoreChange(0);
        }
      } else {
        // No reports — assume full score, empty issues
        setComplianceScore(100);
        setIssueCounts({
          critical: 0,
          high: 0,
          medium: 0,
          low: 0,
          resolved: 0,
        });
        setRecentIssues([]);
        setScoreChange(0);
      }
    };

    fetchLatestReport();
  }, []);


  const getScoreColor = (score:number) => {
    if(score === 100) {
      return 'text-green-600';
    }
    if(score < 100 && score >= 60){
      return 'text-yellow-600';
    }

    return 'text-red-600';
  };

  const getBgColor = (score:number) => {
    if(score === 100) {
      return 'bg-green-50 border-green-600';
    }
    if(score < 100 && score >= 60){
      return 'bg-yellow-50 border-yellow-600';
    }

    return 'bg-red-50 border-red-600';
  };

  const getSeverityColor = (severity: string) => {
    if (severity === 'high'){
      return 'bg-red-100 text-red-600 border-red-200';
    } else if (severity === 'medium'){
      return 'bg-yellow-100 text-yellow-600 border-yellow-200';
    } else if (severity === 'low'){
      return 'bg-green-100 text-green-600 border-green-200';
    } else{
      return 'bg-gray-100 text-gray-600 border-gray-200';
    }
  };

  return (
    <Layout>
      <div className="w-full mx-auto space-y-8">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Compliance Dashboard</h1>
            <p className="text-lg text-slate-600">Monitor you Compliance with your all inclusive Dashboard</p>
          </div>
          <Link href= "/upload">
            <Button className="bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 mt-4 rounded-lg">New Analysis</Button>
          </Link>
        </div>

        <Card className={`${getBgColor(complianceScore)} border-2`}>
          <CardHeader className="pb-3 flex flex-col items-center justify-center text-center">
            <SecurityCameraIcon className="w-10 h-10 text-teal-600 mb-2" />
            <CardTitle className="text-2xl font-bold text-slate-800">
              Overall Score
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center space-y-4 py-4">
              <div className="relative">
                <div className="w-32 h-32 rounded-full border-8 border-slate-600 flex items-center justify-center">
                  <span className={`${getScoreColor(complianceScore)} text-5xl font-extrabold`}>{complianceScore}</span>
                </div>
                <div 
                  className={`absolute inset-0 rounded-full border-slate-200 flex items-center justify-center ${
                    complianceScore >= 100 ? 'border-t-green-500 border-r-green-500' :
                    complianceScore >=60 ? 'border-t-orange-500 border-r-orange-500' :
                    'border-t-red-500 border-r-red-500'
                  }`}
                  style={{
                    transform: `rotate(${complianceScore * 3.6}deg)`,
                    transition: 'transform 0.5s ease-in-out',
                  }}
                />
              </div>
              <p className="text-lg text-slate-600">
                {
                  complianceScore >= 100 ? 'Compliant' :
                  complianceScore >= 60 ? 'Partially Compliant' :
                  'Non-Compliant'
                }
              </p>
              <div className="text-sm text-slate-500">
                <span className={`${scoreChange >= 0 ? "text-green-600" : "text-red-600"} mr-2`}>
                  {scoreChange >= 0 ? `+${scoreChange}` : `${scoreChange}`} points since last check
                </span>
                <span>
                  Last Update: {new Date().toLocaleDateString()}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid md:grid-cols-2 gap-4 lg:grid-cols-4 gaps-5">
          <Card className="bg-red-700 border-black">
            <CardHeader className="pb-2">
              <CardTitle className="text-md font-medium text-white flex-items-center">
                <WarningCircleIcon className="w-7 h-7 mr-2"/>
                High Risk Issues 
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-white">
                {issueCounts.high}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-orange-700 border-black">
            <CardHeader className="pb-2">
              <CardTitle className="text-md font-medium text-white flex-items-center">
                <HourglassSimpleIcon className="w-7 h-7 mr-2"/>
                Medium Risk Issues 
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-white">
                {issueCounts.medium}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-yellow-600 border-black">
            <CardHeader className="pb-2">
              <CardTitle className="text-md font-medium text-white flex-items-center">
                <AsteriskIcon className="w-7 h-7 mr-2"/>
                Low Risk Issues 
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-white">
                {issueCounts.low}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-green-600 border-black">
            <CardHeader className="pb-2">
              <CardTitle className="text-md font-medium text-white flex-items-center">
                <CheckFatIcon className="w-7 h-7 mr-2"/>
                Resolved Issues 
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-white">
                {issueCounts.resolved}
              </div>
            </CardContent>
          </Card>
        </div>

        {(issueCounts.high + issueCounts.critical) > 0 && (
          <Alert className="border-red-800 bg-red-50 p-4 flex flex-col items-center text-center">
            <WarningIcon className="w-5 h-5 text-red-800 mb-2" />
            <AlertDescription className="text-lg text-red-800">
              You have {issueCounts.high + issueCounts.critical} urgent compliance issues that are ready for review.
            </AlertDescription>
          </Alert>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <FileTextIcon className="w-7 h-7 text-slate-800"/>
                Recent Issues
              </div>
              <Link href="/reports">
                <Button variant="outline" size="sm" >View All</Button>
              </Link>
            </CardTitle>
          </CardHeader>
          <CardContent className="max-h-80 overflow-y-auto space-y-4">
            {recentIssues.length === 0 ? (
              <div className="text-center text-slate-500 py-8 text-sm">
                🎉 No recent compliance issues found!
              </div>
            ) : (
              <div className="space-y-4">
                {recentIssues.map((issue: any, index: number) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h4 className="font-medium text-slate-800 break-words whitespace-normal text-sm">
                          {issueName || "No description provided"}
                        </h4>
                        <Badge className={`text-xs ${getSeverityColor(issue.severity)}`}>
                          {issue.severity.toUpperCase()}
                        </Badge>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600 mt-1">
                        <span>{issue.law || "Unknown Law"}</span>
                        <span>&middot;</span>
                        <span>{issue.severity || "Unknown Severity"}</span>
                        <span>&middot;</span>
                        <span>{new Date().toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

      </div>  
    </Layout>
  )
};

export default Home;