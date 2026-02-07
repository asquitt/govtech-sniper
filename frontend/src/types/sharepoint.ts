export interface SharePointFile {
  id: string;
  name: string;
  is_folder: boolean;
  size: number;
  last_modified?: string | null;
  web_url?: string | null;
}

export interface SharePointUploadResult {
  id: string;
  name: string;
  web_url?: string | null;
  size: number;
}

export interface SharePointStatus {
  configured: boolean;
  enabled: boolean;
  connected: boolean;
  error?: string;
}
