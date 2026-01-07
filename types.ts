export enum AppStep {
  UPLOAD = 'UPLOAD',
  ANALYSIS = 'ANALYSIS',
  REVIEW = 'REVIEW',
  EXPORT = 'EXPORT'
}

export enum RelevanceStatus {
  PENDING = 'pending',
  // Standard Backend Statuses
  KEPT = 'kept',
  DELETED = 'deleted',
  UNDECIDED = 'undecided',
  AUTO = 'AUTO',

  // Legacy or Future Use
  HIGH_RELEVANCE = 'HIGH_RELEVANCE', // > 80 score
  MEDIUM_RELEVANCE = 'MEDIUM_RELEVANCE', // 40-80 score, needs human review
  LOW_RELEVANCE = 'LOW_RELEVANCE', // < 40 score
  MACHINE_VERIFIED = 'MACHINE_VERIFIED', // Machine checked secondary flow
  REJECTED = 'REJECTED',
  APPROVED = 'APPROVED'
}

export interface KeywordItem {
  id: string;
  originalText: string;
  score: number; // 0-100
  reasoning?: string;
  status: RelevanceStatus;
  searchVolume?: number; // Optional metadata from excel
}

export interface ProductContext {
  imageFile: File | null;
  imageData: string | null; // Base64
  description: string;
  category: string;
  visualFeatures: string[];
}

export interface AnalysisStats {
  total: number;
  processed: number;
  approved: number;
  rejected: number;
  needsReview: number;
  currentBatch: number;
}