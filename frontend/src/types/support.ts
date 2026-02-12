export interface HelpArticle {
  id: string;
  title: string;
  category: string;
  summary: string;
  content: string;
  tags: string[];
  last_updated: string;
}

export interface TutorialStep {
  title: string;
  instruction: string;
  route: string;
  action_label?: string | null;
}

export interface InteractiveTutorial {
  id: string;
  title: string;
  feature: string;
  estimated_minutes: number;
  steps: TutorialStep[];
}

export interface SupportChatRequest {
  message: string;
  current_route?: string;
}

export interface SupportChatResponse {
  reply: string;
  suggested_article_ids: string[];
  suggested_tutorial_id: string | null;
  generated_at: string;
}
