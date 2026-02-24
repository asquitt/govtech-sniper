"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type {
  IntegrationProvider,
  IntegrationProviderDefinition,
} from "@/types";

interface IntegrationFormProps {
  provider: IntegrationProvider;
  providerOptions: { value: IntegrationProvider; label: string }[];
  selectedDefinition: IntegrationProviderDefinition | undefined;
  name: string;
  fieldValues: Record<string, string>;
  onProviderChange: (provider: IntegrationProvider) => void;
  onNameChange: (name: string) => void;
  onFieldChange: (key: string, value: string) => void;
  onCreate: () => void;
}

export function IntegrationForm({
  provider,
  providerOptions,
  selectedDefinition,
  name,
  fieldValues,
  onProviderChange,
  onNameChange,
  onFieldChange,
  onCreate,
}: IntegrationFormProps) {
  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-4">
        <p className="text-sm font-medium">Add Integration</p>
        <div className="grid grid-cols-3 gap-3">
          <select
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            value={provider}
            onChange={(e) => onProviderChange(e.target.value as IntegrationProvider)}
          >
            {providerOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Name (optional)"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
          />
          <div className="rounded-md border border-border bg-background px-2 py-1 text-sm flex items-center text-muted-foreground">
            {selectedDefinition?.category || "Loading provider fields"}
          </div>
        </div>

        {selectedDefinition ? (
          <div className="space-y-3">
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">Required fields</p>
              <div className="grid grid-cols-2 gap-3">
                {selectedDefinition.required_fields.map((field) => (
                  <input
                    key={field.key}
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder={field.label}
                    type={field.secret ? "password" : "text"}
                    value={fieldValues[field.key] || ""}
                    onChange={(e) => onFieldChange(field.key, e.target.value)}
                  />
                ))}
              </div>
            </div>
            {selectedDefinition.optional_fields.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Optional fields</p>
                <div className="grid grid-cols-2 gap-3">
                  {selectedDefinition.optional_fields.map((field) => (
                    <input
                      key={field.key}
                      className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                      placeholder={field.label}
                      type={field.secret ? "password" : "text"}
                      value={fieldValues[field.key] || ""}
                      onChange={(e) => onFieldChange(field.key, e.target.value)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            Provider definitions are loading.
          </p>
        )}

        <Button onClick={onCreate}>Create Integration</Button>
      </CardContent>
    </Card>
  );
}
