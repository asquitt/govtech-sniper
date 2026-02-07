"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Rocket,
  Building2,
  Link2,
  FileSearch,
  PartyPopper,
  ChevronRight,
  ChevronLeft,
  SkipForward,
} from "lucide-react";

const COMMON_NAICS = [
  { code: "541511", label: "Custom Computer Programming" },
  { code: "541512", label: "Computer Systems Design" },
  { code: "541519", label: "Other Computer Related Services" },
  { code: "541611", label: "Administrative Management Consulting" },
  { code: "541613", label: "Marketing Consulting" },
  { code: "541690", label: "Other Scientific & Technical Consulting" },
  { code: "541715", label: "R&D in Physical & Life Sciences" },
  { code: "561210", label: "Facilities Support Services" },
  { code: "611430", label: "Professional Development Training" },
  { code: "518210", label: "Data Processing & Hosting" },
];

interface SetupWizardProps {
  onComplete: () => void;
}

export function SetupWizard({ onComplete }: SetupWizardProps) {
  const [step, setStep] = useState(0);
  const [companyName, setCompanyName] = useState("");
  const [title, setTitle] = useState("");
  const [selectedNaics, setSelectedNaics] = useState<string[]>([]);

  const steps = [
    { icon: Rocket, label: "Welcome" },
    { icon: Building2, label: "NAICS Codes" },
    { icon: Link2, label: "Integrations" },
    { icon: FileSearch, label: "First RFP" },
    { icon: PartyPopper, label: "Done" },
  ];

  const toggleNaics = (code: string) => {
    setSelectedNaics((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const next = () => setStep((s) => Math.min(s + 1, steps.length - 1));
  const back = () => setStep((s) => Math.max(s - 1, 0));

  const renderStep = () => {
    switch (step) {
      case 0:
        return (
          <div className="space-y-4 text-center">
            <Rocket className="w-16 h-16 mx-auto text-primary" />
            <h2 className="text-2xl font-bold text-foreground">
              Welcome to RFP Sniper
            </h2>
            <p className="text-muted-foreground max-w-md mx-auto">
              Let&apos;s set up your account so you can start winning government
              contracts faster with AI.
            </p>
            <div className="space-y-3 max-w-sm mx-auto text-left">
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Company Name
                </label>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="Acme Federal Solutions"
                  className="w-full px-3 py-2 rounded-md border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Your Title
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Capture Manager"
                  className="w-full px-3 py-2 rounded-md border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
          </div>
        );

      case 1:
        return (
          <div className="space-y-4">
            <div className="text-center">
              <Building2 className="w-12 h-12 mx-auto text-primary mb-2" />
              <h2 className="text-xl font-bold text-foreground">
                Select Your NAICS Codes
              </h2>
              <p className="text-sm text-muted-foreground">
                Choose the codes that match your capabilities
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg mx-auto">
              {COMMON_NAICS.map((n) => (
                <button
                  key={n.code}
                  onClick={() => toggleNaics(n.code)}
                  className={`text-left px-3 py-2 rounded-md border text-sm transition-colors ${
                    selectedNaics.includes(n.code)
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border text-foreground hover:bg-muted"
                  }`}
                >
                  <span className="font-mono text-xs text-muted-foreground">
                    {n.code}
                  </span>
                  <br />
                  {n.label}
                </button>
              ))}
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-4 text-center">
            <Link2 className="w-12 h-12 mx-auto text-primary" />
            <h2 className="text-xl font-bold text-foreground">
              Available Integrations
            </h2>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Connect your tools to streamline your workflow. You can set these
              up later from Settings.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md mx-auto">
              {[
                { name: "SAM.gov", desc: "Auto-ingest opportunities" },
                { name: "SharePoint", desc: "Document storage" },
                { name: "Salesforce", desc: "CRM sync" },
                { name: "Slack", desc: "Team notifications" },
              ].map((i) => (
                <div
                  key={i.name}
                  className="p-3 rounded-lg border border-border text-left"
                >
                  <p className="font-medium text-foreground text-sm">
                    {i.name}
                  </p>
                  <p className="text-xs text-muted-foreground">{i.desc}</p>
                </div>
              ))}
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-4 text-center">
            <FileSearch className="w-12 h-12 mx-auto text-primary" />
            <h2 className="text-xl font-bold text-foreground">
              Add Your First Opportunity
            </h2>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Head to the Opportunities page and click &quot;Ingest from
              SAM.gov&quot; to pull in a solicitation by Notice ID, or upload an
              RFP document directly.
            </p>
            <div className="bg-muted/30 rounded-lg p-4 max-w-md mx-auto text-left space-y-2">
              <p className="text-sm text-foreground font-medium">Quick steps:</p>
              <ol className="text-sm text-muted-foreground space-y-1 list-decimal list-inside">
                <li>Go to Opportunities in the sidebar</li>
                <li>Click &quot;Ingest&quot; and paste a SAM.gov Notice ID</li>
                <li>RFP Sniper will analyze it automatically</li>
                <li>Review the AI analysis and start your proposal</li>
              </ol>
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-4 text-center">
            <PartyPopper className="w-16 h-16 mx-auto text-primary" />
            <h2 className="text-2xl font-bold text-foreground">
              You&apos;re All Set!
            </h2>
            <p className="text-muted-foreground max-w-md mx-auto">
              Your account is ready. Start exploring opportunities and let AI
              help you write winning proposals.
            </p>
            <Button size="lg" onClick={onComplete}>
              Go to Dashboard
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/95 backdrop-blur-sm">
      <Card className="w-full max-w-2xl mx-4">
        <CardContent className="pt-6">
          {/* Progress bar */}
          <div className="flex items-center justify-center gap-2 mb-8">
            {steps.map((s, i) => (
              <React.Fragment key={i}>
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-colors ${
                    i <= step
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {i + 1}
                </div>
                {i < steps.length - 1 && (
                  <div
                    className={`w-8 h-0.5 ${
                      i < step ? "bg-primary" : "bg-muted"
                    }`}
                  />
                )}
              </React.Fragment>
            ))}
          </div>

          {/* Step content */}
          <div className="min-h-[300px] flex items-center justify-center">
            {renderStep()}
          </div>

          {/* Navigation */}
          {step < 4 && (
            <div className="flex justify-between mt-6 pt-4 border-t border-border">
              <Button
                variant="ghost"
                onClick={back}
                disabled={step === 0}
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                Back
              </Button>
              <div className="flex gap-2">
                <Button variant="ghost" onClick={onComplete}>
                  <SkipForward className="w-4 h-4 mr-1" />
                  Skip
                </Button>
                <Button onClick={next}>
                  Next
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
