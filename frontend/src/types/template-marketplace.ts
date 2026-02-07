export interface MarketplaceTemplate {
  id: number;
  name: string;
  category: string;
  subcategory: string | null;
  description: string;
  placeholders: Record<string, string>;
  keywords: string[];
  usage_count: number;
  is_public: boolean;
  rating_sum: number;
  rating_count: number;
  forked_from_id: number | null;
  user_id: number | null;
  created_at: string;
}

export interface TemplateRating {
  rating: number; // 1-5
}
